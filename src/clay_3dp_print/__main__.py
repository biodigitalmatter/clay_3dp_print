import os
import sys

from compas import json_load
import compas_rrc as rrc
from compas.geometry import Vector

# IP = "192.168.8.30" # cook
IP = None  # localhost

WOBJ = "wobj_pallet_markers"
TOOL = "t_erratic_t25"


def main(filepath: os.PathLike):
    frames = json_load(filepath)
    safety_z = Vector(0, 0, 50)

    for layer in frames:
        for frame in layer:
            frame.point += safety_z

    first_frame = frames[0].pop(0)

    # Create Ros Client
    ros = rrc.RosClient()
    ros.run()

    # Create ABB Client
    abb = rrc.AbbClient(ros, "/rob1")
    print("Connected.")

    # Define robot joints
    robot_joints_start_position = robot_joints_end_position = [100, 20, 25, 5, -40, -10]

    # Define external axis
    external_axis_dummy = []

    # Define speed
    speed = 150
    speed_print = 50

    # Set Acceleration
    acc = 100  # Unit [%]
    ramp = 100  # Unit [%]
    abb.send(rrc.SetAcceleration(acc, ramp))

    # Set Max Speed
    override = 100  # Unit [%]
    max_tcp = 2500  # Unit [mm/s]
    abb.send(rrc.SetMaxSpeed(override, max_tcp))

    # Reset signals
    # abb.send(rrc.SetDigital('do_X',0))
    # abb.send(rrc.SetDigital('do_Y',0))
    # abb.send(rrc.SetDigital('do_Z',0))

    # Set tool
    abb.send(rrc.SetTool(TOOL))

    # Set work object
    abb.send(rrc.SetWorkObject(WOBJ))

    # User message -> basic settings send to robot
    print("Tool, Wobj, Acc and MaxSpeed sent to robot")

    # Stop task user must press play button on the FlexPendant (RobotStudio) before robot starts to move
    abb.send(rrc.PrintText("Press Play to move."))
    abb.send(rrc.Stop())

    # Move robot to start position
    abb.send_and_wait(
        rrc.MoveToJoints(
            robot_joints_start_position, external_axis_dummy, speed, rrc.Zone.FINE
        )
    )

    abb.send(rrc.MoveToFrame(first_frame, speed, rrc.Zone.FINE))

    for i, layer in enumerate(frames):
        abb.send(rrc.PrintText(f"Layer {i}"))
        for i, frame in enumerate(layer):
            abb.send(
                rrc.MoveToFrame(
                    frame, speed_print, rrc.Zone.FINE, motion_type=rrc.Motion.LINEAR
                )
            )

    # Move robot to end position
    abb.send(
        rrc.MoveToJoints(
            robot_joints_end_position, external_axis_dummy, speed, rrc.Zone.FINE
        )
    )

    # Print Text
    abb.send_and_wait(rrc.PrintText("Print finished."))

    # Close client
    ros.close()
    ros.terminate()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        main(filepath)
    else:
        print("Usage: clay_3dp_print <filepath>")
