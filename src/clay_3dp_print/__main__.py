import sys
import typing

from compas import json_load
import compas.geometry
from compas_fab.backends import RosClient
from compas_fab.backends.ros.messages import ROSmsg
import compas_rrc as rrc
from clay_3dp_print import PrintLayer

# IP = "192.168.8.30" # cook
IP = "localhost"

WOBJ = "wobj_pallet_markers"
TOOL = "t_erratic_t25"

SPEED = 75
SPEED_PRINT = 50

EXTRUSION_FACTOR_AO = "ao_printPtSpd"

# negative means move towards the sky
Z_ADJUSTMENT = 0


def get_set_extruder(speed_factor: float):
    return rrc.SetAnalog(EXTRUSION_FACTOR_AO, speed_factor)


def get_start_extrude(speed_factor=1):
    return get_set_extruder(speed_factor)


def get_stop_extrude():
    return get_set_extruder(0)


def construct_cmds(layers: list[PrintLayer]) -> typing.Generator[ROSmsg]:
    first_print_frame = layers[0].pop(0)

    first_print_frame.translate_frame_in_local_Z(Z_ADJUSTMENT)

    yield rrc.MoveToFrame(
        first_print_frame, SPEED, rrc.Zone.FINE, motion_type=rrc.Motion.JOINT
    )

    for i, layer in enumerate(layers):
        yield rrc.PrintText(f"Layer {i}")

        x, y, z = layer[0].point
        first_pt_str = f"{x:.2f},{y:.2f},{z:.2f}"

        yield rrc.PrintText(f"First frame: {first_pt_str}")

        for print_frame in layer:
            yield get_set_extruder(print_frame.extrusion_factor)

            print_frame.translate_frame_in_local_Z(Z_ADJUSTMENT)

            if print_frame.is_travel():
                # TODO: Add retraction
                pass

            yield rrc.MoveToFrame(
                print_frame,
                SPEED if print_frame.is_travel() else SPEED_PRINT,
                rrc.Zone.Z1,
                motion_type=rrc.Motion.LINEAR,
                feedback_level=rrc.FeedbackLevel.DONE,
            )


def process_with_batches(
    abb: rrc.AbbClient, cmd_generator: typing.Generator[ROSmsg], batch_size: int = 100
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
    robot_joints_start_position = robot_joints_end_position = [100, 20, 25, 5, -40, -10]

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


def load_json_from_arg1():
    filepath = sys.argv[1]
    data = json_load(filepath)
    frames = data["frames"]
    extrusion_factors = data["extrusion_factors"]

    # put all in one "layer"
    if isinstance(frames[0], compas.geometry.Frame):
        if len(extrusion_factors) == len(frames) - 1:
            # TODO: Fix me
            extrusion_factors.append(True)

        frames = [frames]
        extrusion_factors = [extrusion_factors]

    return [
        PrintLayer.from_frames_and_factors(f, ef)
        for f, ef in zip(frames, extrusion_factors, strict=True)
    ]


def main():
    if len(sys.argv) > 1:
        print_layers = load_json_from_arg1()
        robot_program(print_layers)
    else:
        print("Usage: clay_3dp_print <filepath>")


if __name__ == "__main__":
    main()
