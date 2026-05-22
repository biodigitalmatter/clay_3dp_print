import sys
import time
from typing import Generator

import compas.geometry
import compas_rrc as rrc
from compas import json_load
from compas.geometry import Frame
from compas_fab.backends import RosClient
from compas_fab.backends.ros.messages import ROSmsg

from clay_3dp_print import PrintFrame, PrintLayer
from clay_3dp_print.list_operations import iterate_nested_lists

# IP = "192.168.8.30" # cook
IP = "localhost"

WOBJ = "wobj_pallet_markers"
TOOL = "t_erratic_t25"
SPEED = 150
SPEED_PRINT = 50

EXTRUSION_FACTOR_DO = "ao_printPtSpd"

# negative Z means move towards the sky
XYZ_ADJUSTMENT = (0, 0, 6)

Z_HOP = -50


def get_set_extruder(speed_factor: float) -> ROSmsg:
    return rrc.SetAnalog(EXTRUSION_FACTOR_DO, speed_factor)


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
                SPEED_PRINT,
                rrc.Zone.Z5,
                motion_type=rrc.Motion.LINEAR,
                feedback_level=rrc.FeedbackLevel.DONE,
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
    exhausted = False

    def send_next():
        nonlocal commands_sent, exhausted

        try:
            cmd = next(cmd_generator)
        except StopIteration:
            exhausted = True
            return False

        feedback = abb.send(cmd)
        if feedback:
            futures.append(feedback)

        commands_sent += 1
        return True

    # Send the first batch
    for _ in range(batch_size):
        if not send_next():
            break

    while not exhausted or len(futures) > 0:
        completed = []
        for f in futures:
            if not f:
                continue
            try:
                f.result(timeout=3)
                completed.append(f)
            except rrc.TimeoutException:
                continue

        # Remove completed futures
        for f in completed:
            futures.remove(f)

        if completed:
            refill_count = len(completed)
        elif futures:
            refill_count = 0
        else:
            refill_count = 1

        for _ in range(refill_count):
            if not send_next():
                break


def robot_program(layers: list[PrintLayer]):
    # breakpoint()
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

        for i, cmd in enumerate(cmd_generator):
            abb.send(cmd)
            if i % 100 == 0:
                time.sleep(5)

        process_with_batches(abb, cmd_generator, batch_size=100)

        # Move robot to end position
        abb.send(
            rrc.MoveToJoints(
                robot_joints_end_position, external_axis_dummy, SPEED, rrc.Zone.FINE
            )
        )

        # Print Text
        abb.send_and_wait(rrc.PrintText("Print finished."))


def load_json_from_arg1():
    filepath = sys.argv[1]
    data = json_load(filepath)
    frames = data["frames"]
    extrusion_factors = data["extrusion_factors"]

    while len(frames) == 1:
        frames = frames[0]

    # assumes list of layers of frames
    print_layers = []
    for layer_f, layer_e in zip(frames, extrusion_factors):
        print_layers.append(PrintLayer.from_frames_and_factors(layer_f, layer_e))

    return print_layers
    return [
        PrintLayer.from_frames_and_factor(f, 1.0)
        for f in iterate_nested_lists(frames, compas.geometry.Frame)
    ]


def main():
    if len(sys.argv) > 1:
        print_layers = load_json_from_arg1()
        robot_program(print_layers)
    else:
        print("Usage: clay_3dp_print <filepath>")


if __name__ == "__main__":
    main()
