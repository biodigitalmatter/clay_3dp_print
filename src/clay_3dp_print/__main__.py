import sys

from compas import json_load
from compas_fab.backends import RosClient
import compas_rrc as rrc

# IP = "192.168.8.30" # cook
IP = "localhost"

WOBJ = "wobj_pallet_markers"
TOOL = "t_erratic_t25"


def robot_program(frames):
    # Define robot joints
    robot_joints_start_position = robot_joints_end_position = [100, 20, 25, 5, -40, -10]

    # Define external axis
    external_axis_dummy = []

    speed = 150
    speed_print = 50
    acc = 100  # Unit [%]
    ramp = 100  # Unit [%]
    override = 100  # Unit [%]
    max_tcp = 2500  # Unit [mm/s]

    # safety_z = Vector(0, 0, 10)
    # for layer in frames:
    #     for frame in layer:
    #         frame.point += safety_z

    first_frame = frames[0].pop(0)

    with RosClient(host=IP, port=9090) as ros:
        abb = rrc.AbbClient(ros, "/rob1")
        print("Connected.")

        abb.send(rrc.SetAcceleration(acc, ramp))
        abb.send(rrc.SetMaxSpeed(override, max_tcp))

        # Reset signals
        # abb.send(rrc.SetDigital('do_X',0))
        # abb.send(rrc.SetDigital('do_Y',0))
        # abb.send(rrc.SetDigital('do_Z',0))

        abb.send(rrc.SetTool(TOOL))
        abb.send(rrc.SetWorkObject(WOBJ))

        # User message -> basic settings send to robot
        print("Tool, Wobj, Acc and MaxSpeed sent to robot")

        # Stop task user must press play button on the FlexPendant (RobotStudio)
        # before robot starts to move
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
            x, y, z = layer[0].point
            first_pt_str = f"{x:.2f},{y:.2f},{z:.2f}"

            abb.send(rrc.PrintText(f"First frame: {first_pt_str}"))
            for i, frame in enumerate(layer):
                abb.send(
                    rrc.MoveToFrame(
                        frame, speed_print, rrc.Zone.Z1, motion_type=rrc.Motion.LINEAR
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


def main():
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        frames = json_load(filepath)
        robot_program(frames)
    else:
        print("Usage: clay_3dp_print <filepath>")


if __name__ == "__main__":
    main()
