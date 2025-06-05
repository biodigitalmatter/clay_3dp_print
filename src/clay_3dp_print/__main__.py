import sys
from typing import Generator

import compas_rrc as rrc
from compas.geometry import Frame
from compas_fab.backends import RosClient
from compas_fab.backends.ros.messages import ROSmsg

from clay_3dp_print import PrintFrame, PrintLayer
from clay_3dp_print.toolpath_loader import load_print_layers_from_compas_json_dump

# IP = "192.168.8.30" # cook
IP = "localhost"

WOBJ = "wobj_pallet_markers"
TOOL = "t_erratic_t25"
SPEED = 150
SPEED_PRINT = 50

EXTRUSION_FACTOR_AO = "ao_printPtSpd"

# negative Z means move towards the sky
XYZ_ADJUSTMENT = (0, 0, 6)

Z_HOP = -50


def get_set_extruder(speed_factor: float) -> ROSmsg:
    return rrc.SetAnalog(EXTRUSION_FACTOR_AO, speed_factor)


def get_start_extrude(speed_factor: float = 1.0):
    return get_set_extruder(speed_factor)


def get_stop_extrude() -> ROSmsg:
    return get_set_extruder(0)


def construct_cmds(layers: list[PrintLayer]) -> Generator[ROSmsg]:
    f = layers[0][0]
    z_hop_first_layer = PrintFrame(Frame(f.point, xaxis=f.xaxis, yaxis=f.yaxis), 0)
    # z_hop_first_layer = PrintFrame(f.copy(), 0)

    z_hop_first_layer.translate_frame_in_local_Z(Z_HOP)

    print(f"First before print Z: {z_hop_first_layer.zaxis}")

    yield rrc.MoveToFrame(
        z_hop_first_layer, SPEED, rrc.Zone.FINE, motion_type=rrc.Motion.JOINT
    )

    last_was_travel = False
    for i, layer in enumerate(layers):
        yield rrc.PrintText(f"Layer {i}")

        first_frame = layer[0]
        x, y, z = first_frame.point
        first_pt_str = f"{x:.2f},{y:.2f},{z:.2f}"

        yield rrc.PrintText(f"First frame: {first_pt_str}")

        z_hop_frame = PrintFrame(Frame(f.point, xaxis=f.xaxis, yaxis=f.yaxis), 0)

        z_hop_frame.translate_frame_in_local_Z(Z_HOP)
        yield rrc.MoveToFrame(
            z_hop_frame,
            SPEED,
            rrc.Zone.Z10,
            motion_type=rrc.Motion.JOINT,
            feedback_level=rrc.FeedbackLevel.DONE,
        )
        yield rrc.MoveToFrame(
            first_frame,
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
                rrc.Zone.Z2,
                motion_type=rrc.Motion.LINEAR,
            )

        yield get_set_extruder(0)

        z_hop_frame = PrintFrame(
            Frame(print_frame.point, print_frame.xaxis, print_frame.yaxis), 0
        )
        z_hop_frame.translate_frame_in_local_Z(Z_HOP)

        yield rrc.MoveToFrame(
            z_hop_frame,
            SPEED,
            rrc.Zone.Z10,
            motion_type=rrc.Motion.JOINT,
            feedback_level=rrc.FeedbackLevel.DONE,
        )


def process_with_batches(
    abb: rrc.AbbClient, cmd_generator: Generator[ROSmsg], batch_size: int = 100
):
    futures = []
    commands_sent = 0

    # Send the first batch
    for _ in range(batch_size):
        try:
            cmd = next(cmd_generator)

            feedback = abb.send(cmd)

            if feedback:
                futures.append(feedback)

            commands_sent += 1
        except StopIteration:
            break

    while futures:
        completed = []
        for f in futures:
            try:
                f.result(timeout=3)
                completed.append(f)
            except rrc.TimeoutException:
                continue

        # Remove completed futures
        for f in completed:
            futures.remove(f)

        # Add more commands to maintain the buffer
        for _ in range(len(completed)):
            try:
                cmd = next(cmd_generator)

                feedback = abb.send(cmd)

                if feedback:
                    futures.append(feedback)
                commands_sent += 1
            except StopIteration:
                break


def robot_program(layers: list[PrintLayer]):
    # Define robot joints
    robot_joints_start_position = robot_joints_end_position = [-71, 8, 34, 99, -94, -58]

    # Define external axis
    external_axis_dummy = []

    acc = 70  # Unit [%]
    ramp = 100  # Unit [%]
    override = 100  # Unit [%]
    max_tcp = 250  # Unit [mm/s]

    cmd_generator = construct_cmds(layers)

    with RosClient(host=IP, port=9090) as ros:
        abb = rrc.AbbClient(ros, "/rob1")
        print("Connected.")

        abb.send(rrc.SetAcceleration(acc, ramp))
        abb.send(rrc.SetMaxSpeed(override, max_tcp))

        abb.send(get_stop_extrude())  # reset signal

        abb.send(rrc.SetTool(TOOL))
        abb.send(rrc.SetWorkObject(WOBJ))

        # User message -> basic settings send to robot
        print("Tool, Wobj, Acc and MaxSpeed sent to robot")

        # Stop task user must press play button on the FlexPendant (RobotStudio)
        # before robot starts to move
        abb.send(rrc.PrintText("Press Play to move."))
        abb.send(rrc.Stop())

        # Move robot to start position
        abb.send(
            rrc.MoveToJoints(
                robot_joints_start_position, external_axis_dummy, SPEED, rrc.Zone.FINE
            )
        )

        last_future: rrc.FutureResult | None = None
        counter = 0
        for cmd in cmd_generator:
            ret = abb.send(cmd)

            if ret:
                last_future = ret

            counter += 1

            if counter % 250 == 0 and last_future:
                last_future.result()

        # process_with_batches(abb, cmd_generator)

        # move robot to end position
        abb.send(
            rrc.MoveToJoints(
                robot_joints_end_position, external_axis_dummy, SPEED, rrc.Zone.FINE
            )
        )

        # Print Text
        abb.send_and_wait(rrc.PrintText("Print finished."))


def main():
    if len(sys.argv != 2):
        print("Usage: clay_3dp_print <filepath>")

    print_layers = load_print_layers_from_compas_json_dump(sys.argv[1])
    robot_program(print_layers)


if __name__ == "__main__":
    main()
