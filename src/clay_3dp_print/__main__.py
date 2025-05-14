import sys

from compas import json_load
import compas.geometry
from compas_fab.backends import RosClient
import compas_rrc as rrc

# IP = "192.168.8.30" # cook
IP = "localhost"

WOBJ = "wobj_pallet_markers"
TOOL = "t_erratic_t25"

DRY_RUN = False

SPEED = 75
SPEED_PRINT = 50


def get_set_extruder(state: int):
    return rrc.SetDigital("do_extrudeRelSpd", state)


def get_start_extrude():
    if not DRY_RUN:
        return get_set_extruder(1)


def get_stop_extrude():
    if not DRY_RUN:
        return get_set_extruder(0)


def construct_cmds(frames, travel):
    last_was_t = True

    cmds = []
    for i, (lframes, ltravel) in enumerate(zip(frames, travel)):
        lcmds = []

        lcmds.append(rrc.PrintText(f"Layer {i}"))

        x, y, z = lframes[0].point
        first_pt_str = f"{x:.2f},{y:.2f},{z:.2f}"

        lcmds.append(rrc.PrintText(f"First frame: {first_pt_str}"))

        for f, t in zip(lframes, ltravel, strict=True):
            if not DRY_RUN:
                if not t and last_was_t:
                    lcmds.append(get_start_extrude())

                if t and not last_was_t:
                    lcmds.append(get_stop_extrude())

            lcmds.append(
                rrc.MoveToFrame(
                    f,
                    SPEED if t else SPEED_PRINT,
                    rrc.Zone.Z1,
                    motion_type=rrc.Motion.LINEAR,
                )
            )
            last_was_t = t

        cmds.append(lcmds)
    return cmds


def robot_program(
    frames: list[list[compas.geometry.Frame]], travel: list[list[bool]] | None
):
    # Define robot joints
    robot_joints_start_position = robot_joints_end_position = [100, 20, 25, 5, -40, -10]

    # Define external axis
    external_axis_dummy = []

    acc = 70  # Unit [%]
    ramp = 100  # Unit [%]
    override = 100  # Unit [%]
    max_tcp = 250  # Unit [mm/s]

    z_adjustment_mm = -3  # negative means raise up printbed

    if z_adjustment_mm != 0:
        for layer in frames:
            for frame in layer:
                v = frame.normal.copy()
                v.scale(z_adjustment_mm)
                frame.point.translate(v)

    first_frame = frames[0].pop(0)
    _ = travel[0].pop(0)

    cmds = construct_cmds(frames, travel)

    with RosClient(host=IP, port=9090) as ros:
        abb = rrc.AbbClient(ros, "/rob1")
        print("Connected.")

        abb.send(rrc.SetAcceleration(acc, ramp))
        abb.send(rrc.SetMaxSpeed(override, max_tcp))

        if not DRY_RUN:
            abb.send_and_wait(get_stop_extrude())  # reset signal

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
                robot_joints_start_position, external_axis_dummy, SPEED, rrc.Zone.FINE
            )
        )

        abb.send(rrc.MoveToFrame(first_frame, SPEED, rrc.Zone.FINE))

        for lcmds in cmds:
            abb.send_and_wait(lcmds.pop(0))
            for c in lcmds:
                abb.send(c)

        if not DRY_RUN:
            abb.send_and_wait((get_stop_extrude()))

        # Move robot to end position
        abb.send(
            rrc.MoveToJoints(
                robot_joints_end_position, external_axis_dummy, SPEED, rrc.Zone.FINE
            )
        )

        # Print Text
        abb.send_and_wait(rrc.PrintText("Print finished."))


def main():
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        data = json_load(filepath)
        frames = data["frames"]
        travel = data["travel"]

        # put all in one "layer"
        if isinstance(frames[0], compas.geometry.Frame):
            frames = [frames]
            travel = [travel]

        print(len(frames))
        print(len(travel))
        print(len(frames[0]))
        print(len(travel[0]))

        robot_program(frames, travel)
    else:
        print("Usage: clay_3dp_print <filepath>")


if __name__ == "__main__":
    main()
