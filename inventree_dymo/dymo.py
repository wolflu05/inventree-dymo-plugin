import enum
import math
from typing import Literal, Union

from PIL import Image


class LabeledEnum(enum.IntEnum):
    def __new__(cls, value, label):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj
    
    def __str__(self):
        return self.label

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}: {self.label} ({self.value})>"


class TapeType(LabeledEnum):
    BLACK_ON_WHITE_CLEAR = 0, "Black on White or clear"
    BLACK_ON_BLUE = 1, "Black on Blue"
    BLACK_ON_RED = 2, "Black on Red"
    BLACK_ON_SILVER = 3, "Black on Silver"
    BLACK_ON_YELLOW = 4, "Black on Yellow"
    BLACK_ON_GOLD = 5, "Black on Gold"
    BLACK_ON_GREEN = 6, "Black on Green"
    BLACK_ON_FLUORESCENT_GREEN = 7, "Black on Fluorescent Green"
    BLACK_ON_FLUORESCENT_RED = 8, "Black on Fluorescent Red"
    WHITE_ON_CLEAR = 9, "White on Clear"
    WHITE_ON_BLACK = 10, "White on Black"
    BLUE_ON_WHITE_OR_CLEAR = 11, "Blue on White or Clear"
    RED_ON_WHITE_OR_CLEAR = 12, "Red on White or Clear"


class PrintDensity(LabeledEnum):
    LIGHT = ord("c"), "Light"
    MEDIUM = ord("d"), "Medium"
    NORMAL = ord("e"), "Normal"
    DARK = ord("g"), "Dark"


class RoleSelect(LabeledEnum):
    AUTOMATIC = 0x30, "Automatic selection"
    LEFT_ROLL = 0x31, "Left roll"
    RIGHT_ROLL = 0x32, "Right roll"


class DymoProtocolBuilder:
    def __init__(self):
        self.data = bytearray()
        self.dot_tab = None
        self.bytes_per_line = None

    @staticmethod
    def _to_bytes(value: int):
        return value.to_bytes(2, 'big', signed=True)
    
    def raw(self, data: list[int]):
        self.data += bytearray(data)

    def set_dot_tab(self, tab: int):
        if tab != self.dot_tab:
            self.dot_tab = tab
            self.raw([0x1b, ord("B"), tab])

    def set_bytes_per_line(self, count: int):
        if count != self.bytes_per_line:
            self.bytes_per_line = count
            self.raw([0x1b, ord("D"), count])
    
    def set_label_length(self, length: int):
        self.raw([0x1b, ord("L"), *self._to_bytes(length)])

    def form_feed(self):
        self.raw([0x1b, ord("E")])

    def short_form_feed(self):
        self.raw([0x1b, ord("G")])

    def select_roll(self, role: RoleSelect):
        self.raw([0x1b, ord("q"), role.value])

    def get_printer_status(self):
        self.raw([0x1b, ord("A")])

    def reset_printer(self):
        self.raw([0x1b, ord("@")])

    def restore_default_settings(self):
        self.raw([0x1b, ord("*")])

    def skip_lines(self, count: int):
        self.raw([0x1b, ord("f"), 0x1, count])

    def return_rev_letter_number(self):
        self.raw([0x1b, ord("V")])

    def transfer_data(self, data: bytes):
        self.raw([0x16, *data])

    def transfer_compressed_data(self, data: list[tuple[int, int]]):
        data = [(color << 7) + cnt - 1 for cnt, color in data]
        self.raw([0x17, *data])

    def set_print_mode(self, mode: Literal["TEXT", "GRAPHIC"]):
        if mode == "TEXT":
            self.raw([0x1b, ord("h")])
        elif mode == "GRAPHIC":
            self.raw([0x1b, ord("i")])

    def set_print_density(self, density: PrintDensity):
        self.raw([0x1b, density.value])

    # Tape printer commands
    def set_tape_type(self, tape_type: TapeType):
        self.raw([0x1b, ord("C"), tape_type.value])

    def cut_tape(self):
        self.raw([0x1b, ord("E")])


class DymoLabelBase:
    def __init__(
        self,
        compressed: bool,
        rotate: int,
        threshold: int,
    ):
        self.compressed = compressed
        self.rotate = rotate
        self.threshold = threshold

        self.pb = DymoProtocolBuilder()
        self.init_job()

    def add_label(self, png: Union[Image.Image, list[Image.Image]]):
        # dump label(s)
        if isinstance(png, list):
            for img in png:
                self.dump_label(img)
        else:
            self.dump_label(png)

    def get_data(self):
        self.end_job()

        return self.pb.data

    # --- helper methods ---
    def dump_line(self, line: list[int]):
        start_byte, end_byte = None, None
        for i in range(len(line)):
            if line[i] > 0:
                if start_byte is None:
                    start_byte = i
                end_byte = i

        # line is empty, send empty line command
        if start_byte is None or end_byte is None:
            self.pb.set_bytes_per_line(0)
            self.pb.transfer_data([])
            return

        byte_count = end_byte - start_byte + 1
        data = line[start_byte:end_byte + 1]

        # compressed can later decide to use uncompressed data if compressed data will be larger
        use_uncompressed = not self.compressed

        if self.compressed:
            compressed = []
            pixels = [int(i) for a in data for i in list('{0:0b}'.format(a).zfill(8))]
            curr = pixels[0]
            start_idx = 0
            for i in range(len(pixels)):
                if pixels[i] != curr or i - start_idx >= 128:
                    compressed += [(i - start_idx, curr)]
                    start_idx = i
                    curr = pixels[i]
            compressed += [(len(pixels) - start_idx, curr)]

            if len(compressed) < len(data):
                self.pb.set_dot_tab(start_byte)
                self.pb.set_bytes_per_line(sum(c[0] for c in compressed) // 8)
                self.pb.transfer_compressed_data(compressed)
            else:
                use_uncompressed = True

        if use_uncompressed:
            self.pb.set_dot_tab(start_byte)
            self.pb.set_bytes_per_line(byte_count)
            self.pb.transfer_data(data)

    def png_to_lines(self, png: Image.Image, *, resize=None):
        png = png.rotate(90 + self.rotate, expand=1)

        if resize is not None:
            png = png.resize((png.width // resize[0], png.height // resize[1]), Image.Resampling.LANCZOS)

        width, height = png.size
        data = png.convert('L').point(lambda x: 0 if x > self.threshold else 1, mode='1').tobytes()
        bytes_per_line = math.ceil(width / 8)
        return [data[y * bytes_per_line:(y + 1) * bytes_per_line] for y in range(height)]
    
    # --- hooks ---
    def init_job(self):
        pass

    def end_job(self):
        pass

    def dump_label(self, png: Image.Image):
        pass


class DymoLabel(DymoLabelBase):
    def __init__(
        self,
        *,
        label_length: int = 3058,
        mode: Literal["TEXT", "GRAPHIC"] = 'TEXT',
        density: PrintDensity = PrintDensity.NORMAL,
        role_select: RoleSelect = RoleSelect.AUTOMATIC,
        compressed: bool = None,
        rotate: int = 0,
        threshold: int = 200,
    ):
        # set default compressed value
        if compressed is None:
            compressed = True

        self.label_length = label_length
        self.mode = mode
        self.density = density
        self.role_select = role_select

        super().__init__(compressed, rotate, threshold)

    def init_job(self):
        self.pb.raw([0x51, 0x0, 0x0])
        self.pb.set_print_density(self.density)
        self.pb.set_label_length(self.label_length)
        self.pb.set_print_mode(self.mode)
        self.pb.select_roll(self.role_select)
        self.pb.set_dot_tab(0)
        self.pb.set_bytes_per_line(84)

    def end_job(self):
        self.pb.form_feed()

    def dump_label(self, png: Image.Image):
        resize = (2, 1) if self.mode == "GRAPHIC" else None
        lines = self.png_to_lines(png, resize=resize)

        last_line_idx = len(lines) - 1
        for i in range(len(lines) - 1, -1, -1):
            if any(lines[i]):
                last_line_idx = i
                break

        i = 0
        empty_lines = 0
        while i < len(lines):
            line = lines[i]

            # in label mode, skip empty lines to reduce output size
            if not any(line):
                empty_lines += 1
                i += 1
                continue
            elif empty_lines > 0:
                self.pb.skip_lines(empty_lines)
                empty_lines = 0

            self.dump_line(line)

            i += 1

            # break if this was the last line that contains data
            if last_line_idx == i:
                break

        self.pb.short_form_feed()


class DymoTape(DymoLabelBase):
    def __init__(
        self,
        *,
        tape_type: TapeType = TapeType.BLACK_ON_WHITE_CLEAR,
        tape_size: int = 24,
        rotate: int = 0,
        threshold: int = 200,
    ):
        self.tape_type = tape_type
        self.tape_size = tape_size

        super().__init__(compressed=False, rotate=rotate, threshold=threshold)
    
    def init_job(self):
        self.pb.raw([0x01])
        self.pb.set_dot_tab(0)
        self.pb.set_bytes_per_line(0)
        self.pb.set_tape_type(self.tape_type)

    def dump_label(self, png: Image.Image):
        lines = self.png_to_lines(png)

        for line in lines:
            # TODO: implement tape offset (based on tape_size)
            # Tape cartridges are not aligned at the bottom of the print head,
            # but instead positioned somewhere in the middle, so a correct offset
            # needs to be found before this can be integrated into the InvenTree driver
            self.dump_line(line)

        self.pb.cut_tape()
