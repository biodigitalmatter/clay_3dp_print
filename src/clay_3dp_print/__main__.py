import sys
from collections.abc import Generator

import compas_rrc as rrc
from compas_fab.backends import RosClient
from compas_fab.backends.ros.messages import ROSmsg

from clay_3dp_print import PrintFrame, PrintLayer
from clay_3dp_print.rrc_streaming import stream_in_batches
from clay_3dp_print.toolpath_loader import load_json_from_arg1

# IP = "192.168.8.30" # cook
IP = "localhost"

WOBJ = "wobj_www"

TOOL = "t_erratic_t25"
SPEED = 150
SPEED_PRINT = 50

EXTRUSION_FACTOR_AO = "ao_printPtSpd"

# negative Z means move towards the sky
XYZ_ADJUSTMENT = (0, 0, -7)

Z_HOP = -50


def get_set_extruder(speed_factor: float) -> ROSmsg:
    return rrc.SetAnalog(EXTRUSION_FACTOR_AO, speed_factor)


def get_start_extrude(speed_factor: float = 1.0):
    return get_set_extruder(speed_factor)


def get_stop_extrude() -> ROSmsg:
    return get_set_extruder(0)


def construct_cmds(layers: list[PrintLayer]) -> Generator[ROSmsg]:
    first_frame_in_first_layer = layers[0][0]

    z_hop_first_layer: PrintFrame = first_frame_in_first_layer.copy()

    z_hop_first_layer.translate_frame_in_local_Z(Z_HOP + XYZ_ADJUSTMENT[2])

    print(f"First before print Z: {z_hop_first_layer.zaxis}")

    yield rrc.MoveToFrame(
        z_hop_first_layer, SPEED, rrc.Zone.FINE, motion_type=rrc.Motion.JOINT
    )

    last_was_travel = False
    for i, layer in enumerate(layers):
        yield rrc.PrintText(f"Layer {i}")

        first_frame_copy: PrintFrame = layer[0].copy()

        first_frame_copy.translate_frame_in_local_Z(XYZ_ADJUSTMENT[2])

        x, y, z = first_frame_copy.point
        first_pt_str = f"{x:.2f},{y:.2f},{z:.2f}"

        yield rrc.PrintText(f"First frame: {first_pt_str}")

        z_hop_frame: PrintFrame = first_frame_copy.copy()

        z_hop_frame.translate_frame_in_local_Z(Z_HOP)
        yield rrc.MoveToFrame(
            z_hop_frame,
            SPEED,
            rrc.Zone.Z10,
            motion_type=rrc.Motion.JOINT,
            feedback_level=rrc.FeedbackLevel.DONE,
        )
        yield rrc.MoveToFrame(
            first_frame_copy,
            SPEED,
            rrc.Zone.FINE,
            motion_type=rrc.Motion.LINEAR,
            feedback_level=rrc.FeedbackLevel.DONE,
        )

        for print_frame in layer:
            yield get_set_extruder(print_frame.extrusion_factor)

            print_frame.translate_frame_in_local_Z(XYZ_ADJUSTMENT[2])

            if print_frame.is_travel() and last_was_travel:
                # TODO: Add retraction
                pass

            last_was_travel = print_frame.is_travel()

            yield rrc.MoveToFrame(
                print_frame,
                SPEED if print_frame.is_travel() else SPEED_PRINT,
                rrc.Zone.Z1,
                motion_type=rrc.Motion.LINEAR,
            )

        yield get_set_extruder(0)

        last_frame_in_layer = layer[-1]
        z_hop_frame = last_frame_in_layer.copy()
        z_hop_frame.extrusion_factor = 0
        z_hop_frame.translate_frame_in_local_Z(Z_HOP)

        yield rrc.MoveToFrame(
            z_hop_frame,
            SPEED,
            rrc.Zone.Z10,
            motion_type=rrc.Motion.JOINT,
            feedback_level=rrc.FeedbackLevel.DONE,
        )


def robot_program(layers: list[PrintLayer]):
    # Define robot joints
    robot_joints_start_position = robot_joints_end_position = [-71, 8, 34, 99, -94, -58]

    # Define external axis
    external_axis_dummy: list[float] = []

    acc = 70  # Unit [%]
    ramp = 100  # Unit [%]
    override = 100  # Unit [%]
    max_tcp = 250  # Unit [mm/s]

    cmd_generator = construct_cmds(layers)

    with RosClient(host=IP, port=9090) as ros:
        abb = rrc.AbbClient(ros, "/rob1")
        print("Connected.")

        _ = abb.send(rrc.SetAcceleration(acc, ramp))
        _ = abb.send(rrc.SetMaxSpeed(override, max_tcp))

        _ = abb.send(get_stop_extrude())  # reset signal

        _ = abb.send(rrc.SetTool(TOOL))
        _ = abb.send(rrc.SetWorkObject(WOBJ))

        # User message -> basic settings send to robot
        print("Tool, Wobj, Acc and MaxSpeed sent to robot")

        # Stop task user must press play button on the FlexPendant (RobotStudio)
        # before robot starts to move
        _ = abb.send(rrc.PrintText("Press Play to move."))
        _ = abb.send(rrc.Stop())

        # Move robot to start position
        _ = abb.send(
            rrc.MoveToJoints(
                robot_joints_start_position, external_axis_dummy, SPEED, rrc.Zone.FINE
            )
        )

        stream_in_batches(abb, cmd_generator)

        # move robot to end position
        _ = abb.send(
            rrc.MoveToJoints(
                robot_joints_end_position, external_axis_dummy, SPEED, rrc.Zone.FINE
            )
        )

        # Print Text
        _ = abb.send_and_wait(rrc.PrintText("Print finished."))


def main():
    if len(sys.argv) == 2:
        print_layers = load_json_from_arg1()
        robot_program(print_layers)
    else:
        print("Usage: clay_3dp_print <filepath>")


if __name__ == "__main__":
    main()
