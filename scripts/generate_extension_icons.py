import os
import struct
import zlib


def create_png(width, height, color_bg=(99, 102, 241, 255), color_fg=(255, 255, 255, 255)):
    """
    Generates a raw PNG icon of specified dimensions with an indigo rounded square background
    and a crisp white center icon mark using Python standard library.
    """
    # Create RGBA buffer
    raw_data = bytearray()
    border_radius = max(2, int(width * 0.2))

    for y in range(height):
        raw_data.append(0)  # Filter type 0 (None)
        for x in range(width):
            # Check rounded corners
            dx = max(border_radius - x, 0, x - (width - 1 - border_radius))
            dy = max(border_radius - y, 0, y - (height - 1 - border_radius))
            is_outside = (dx * dx + dy * dy) > (border_radius * border_radius)

            if is_outside:
                # Transparent corner
                raw_data.extend([0, 0, 0, 0])
                continue

            # Check center mark (briefcase/app icon shape)
            margin = max(3, int(width * 0.25))
            top_margin = max(4, int(height * 0.35))
            bottom_margin = max(3, int(height * 0.25))

            is_briefcase_body = (
                margin <= x < (width - margin) and top_margin <= y < (height - bottom_margin)
            )

            # Handle mark
            handle_width = max(2, int(width * 0.3))
            handle_left = (width - handle_width) // 2
            handle_top = max(2, int(height * 0.22))
            handle_bottom = top_margin
            is_handle = (
                handle_left <= x < (handle_left + handle_width)
                and handle_top <= y < handle_bottom
                and not (handle_left + 1 <= x < (handle_left + handle_width - 1) and handle_top + 1 <= y < handle_bottom)
            )

            if is_briefcase_body or is_handle:
                raw_data.extend(color_fg)
            else:
                raw_data.extend(color_bg)

    # PNG chunks
    def chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)

    compressed_data = zlib.compress(bytes(raw_data), level=9)
    idat = chunk(b"IDAT", compressed_data)
    iend = chunk(b"IEND", b"")

    return header + ihdr + idat + iend


def main():
    icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "extension", "icons")
    os.makedirs(icons_dir, exist_ok=True)

    sizes = [16, 48, 128]
    for size in sizes:
        png_bytes = create_png(size, size)
        filepath = os.path.join(icons_dir, f"icon-{size}.png")
        with open(filepath, "wb") as f:
            f.write(png_bytes)
        print(f"Generated {filepath} ({len(png_bytes)} bytes)")


if __name__ == "__main__":
    main()
