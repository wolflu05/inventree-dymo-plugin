import sys

if len(sys.argv) < 2:
    print(
        f"Convert dymo binary data into a graphic for testing.\nUsage: {sys.argv[0]} <dymo_file> [text|image]"
    )
    sys.exit(1)

with open(sys.argv[1], "rb") as f:
    all_bytes = list(f.read())

COMMANDS = {
    "B": ("<SET DOT TAB>", 1),
    "D": ("<SET BYTES PER LINE>", 1),
    "L": ("<SET LABEL LENGTH>", 2),
    "E": ("<FORM FEED>", 0),
    "G": ("<SHORT FORM FEED>", 0),
    "q": ("<SELECT ROLL>", 1),
    "A": ("<GET PRINTER STATUS>", 0),
    "@": ("<RESET PRINTER>", 0),
    "*": ("<RESTORE DEFAULT SETTINGS>", 0),
    "f": ("<SKIP N LINES>", 2),
    "V": ("<RETURN REVISION NUMBER>", 0),
    "h": ("<TEXT SPEED MODE>", 0),
    "i": ("<BARCODE AND GRAPHICS MODE>", 0),
    "c": ("<SET PRINT DENSITY LIGHT>", 0),
    "d": ("<SET PRINT DENSITY MEDIUM>", 0),
    "e": ("<SET PRINT DENSITY NORMAL>", 0),
    "g": ("<SET PRINT DENSITY DARK>", 0),
}
B_COMMANDS = {ord(k): v for k, v in COMMANDS.items()}
IGNORE_CMDS = [ord("D"), ord("B"), ord("f")]

bytes_per_line = 0
dot_tab = 0
graphic_mode = False

last_escape = False
i = 0
data = []

while i < len(all_bytes):
    b = all_bytes[i]
    if b == 0x1B:
        if all_bytes[i + 1] not in IGNORE_CMDS:
            print("\n<ESC>", end="")

        last_escape = True
        i += 1
    elif b == 0x16:
        line = " " * dot_tab * 8
        for f in all_bytes[i + 1 : i + 1 + bytes_per_line]:
            line += format(f, "08b").replace("0", " ").replace("1", "#")
        data.append(line)
        i += 1 + bytes_per_line
    elif b == 0x17:
        line = " " * dot_tab * 8
        d = 0
        bc = 0
        while d < bytes_per_line * 8:
            c, *x = format(all_bytes[i + 1 + bc], "08b")
            num = int("0b" + "".join(x), 2) + 1
            line += [" ", "#"][int(c)] * num
            d += num
            bc += 1

        data.append(line)
        i += 1 + bc
        assert all_bytes[i] in [0x16, 0x17, 0x1B], (
            [hex(x) for x in all_bytes[i - 2 : i + 3]],
            hex(all_bytes[i]),
        )
    else:
        if b == ord("D"):
            bytes_per_line = int(all_bytes[i + 1])
        if b == ord("B"):
            dot_tab = int(all_bytes[i + 1])
        if b == ord("f"):
            n = int(all_bytes[i + 2])
            data.extend([""] * n)
        if b == ord("i"):
            graphic_mode = True

        if last_escape and b in B_COMMANDS:
            cmd, arg_count = B_COMMANDS[b]
            if b not in IGNORE_CMDS:
                print(
                    f"[{cmd} {' '.join(hex(k) for k in all_bytes[i + 1 : i + 1 + arg_count])}]",
                    end="",
                )
            i += arg_count + 1
        else:
            print(hex(b), end=" ")
            i += 1

        last_escape = False

if len(sys.argv) > 2 and sys.argv[2] == "text":
    print()
    print("\n".join(data))
else:
    from PIL import Image, ImageDraw

    out = Image.new(
        "1", (max(len(x) for x in data) * [1, 2][graphic_mode], len(data)), 1
    )
    d = ImageDraw.Draw(out)
    for y, line in enumerate(data):
        for x, c in enumerate(line):
            p = [(x * 2, y), (x * 2 + 1, y)] if graphic_mode else [(x, y)]
            d.point(p, {"#": 0, " ": 1}[c])

    out.show()
