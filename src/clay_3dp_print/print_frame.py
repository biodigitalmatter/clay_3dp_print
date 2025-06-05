import compas.geometry
from compas.tolerance import TOL


class PrintFrame(compas.geometry.Frame):
    """Frame and extrusion value"""

    def __init__(self, frame: compas.geometry.Frame, extrusion_factor: float):
        super().__init__(
            frame.point, xaxis=frame.xaxis, yaxis=frame.yaxis, name=frame.name
        )
        self.extrusion_factor: float = extrusion_factor

    DATASCHEMA = {
        "type": "object",
        "properties": {
            "point": compas.geometry.Point.DATASCHEMA,
            "xaxis": compas.geometry.Vector.DATASCHEMA,
            "yaxis": compas.geometry.Vector.DATASCHEMA,
            "extrusion_factor": {"type": "number"},
        },
        "required": ["point", "xaxis", "yaxis", "extrusion_factor"],
    }

    @property
    def __data__(self):
        return super().__data__ | {"extrusion_factor": self.extrusion_factor}

    @classmethod
    def __from_data__(cls, data):
        extrusion_factor: float = data.pop("extrusion_factor")
        frame = compas.geometry.Frame.__from_data__(data)

        return cls(frame, extrusion_factor)

    def is_travel(self) -> bool:
        return TOL.is_close(self.extrusion_factor, 0)

    def translate_frame_in_local_Z(self, signed_distance: float) -> None:
        """Translates along local Z axis in place."""
        v = self.normal.copy()
        v.scale(signed_distance)
        self.point.translate(v)
