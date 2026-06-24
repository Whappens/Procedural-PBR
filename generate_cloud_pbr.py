import argparse
import numpy as np
from PIL import Image

def generate_perlin_noise_2d(shape, res):
    """Generates seamless (tileable) 2D Perlin noise. res must be an integer."""
    def f(t):
        return 6*t**5 - 15*t**4 + 10*t**3

    x = np.linspace(0, res, shape, endpoint=False)
    y = np.linspace(0, res, shape, endpoint=False)
    x_grid, y_grid = np.meshgrid(x, y, indexing='ij')

    r0_x = x_grid % 1.0
    r0_y = y_grid % 1.0
    r1_x = r0_x - 1.0
    r1_y = r0_y - 1.0

    # Gradient grid setup
    gradients = np.random.randn(res, res, 2)
    # Normalize gradients to unit vectors for cleaner noise blending distribution
    norm = np.linalg.norm(gradients, axis=-1, keepdims=True)
    gradients = np.where(norm > 0, gradients / norm, gradients)

    # Grid indices for smooth interpolation
    i_x = (x_grid // 1).astype(int)
    i_y = (y_grid // 1).astype(int)

    # Wrap indices cleanly around bounds with modulo operator to fix grid seams
    i_x0 = i_x % res
    i_x1 = (i_x + 1) % res
    i_y0 = i_y % res
    i_y1 = (i_y + 1) % res

    g00 = gradients[i_x0, i_y0]
    g10 = gradients[i_x1, i_y0]
    g01 = gradients[i_x0, i_y1]
    g11 = gradients[i_x1, i_y1]

    # Calculate dot products
    n00 = g00[..., 0] * r0_x + g00[..., 1] * r0_y
    n10 = g10[..., 0] * r1_x + g10[..., 1] * r0_y
    n01 = g01[..., 0] * r0_x + g01[..., 1] * r1_y
    n11 = g11[..., 0] * r1_x + g11[..., 1] * r1_y

    # Smooth curve interpolation via f(t)
    t_x = f(r0_x)
    t_y = f(r0_y)

    n0 = n00 * (1.0 - t_x) + n10 * t_x
    n1 = n01 * (1.0 - t_x) + n11 * t_x
    return n0 * (1.0 - t_y) + n1 * t_y

def create_cloud_pbr(size=2048):
    print(f"Generating cloud textures at {size}x{size} resolution...")

    # Combine multi-octave fractal noise passes
    noise = (
        1.0 * generate_perlin_noise_2d(size, 4) +
        0.5 * generate_perlin_noise_2d(size, 8) +
        0.25 * generate_perlin_noise_2d(size, 16) +
        0.125 * generate_perlin_noise_2d(size, 32)
    )

    # Normalize values into [0, 1] range
    noise = (noise - noise.min()) / (noise.max() - noise.min())
    height_map = np.clip((noise - 0.35) / 0.65, 0, 1)

    # 1. ALBEDO (Solid White Base Color + Height Map driven Alpha transparency channel)
    print("Creating Albedo map...")
    albedo_rgb = np.ones((size, size, 3)) * 255
    albedo_alpha = (height_map * 255).astype(np.uint8)
    albedo_rgba = np.dstack((albedo_rgb, albedo_alpha)).astype(np.uint8)
    Image.fromarray(albedo_rgba).save("cloud_albedo.png")

    # 2. NORMAL MAP (Calculated depth offsets for light scattering shadows)
    print("Generating Normal map...")
    strength = 15.0
    hx = np.roll(height_map, -1, axis=1) - np.roll(height_map, 1, axis=1)
    hy = np.roll(height_map, -1, axis=0) - np.roll(height_map, 1, axis=0)

    dx = hx * strength
    dy = hy * strength
    dz = np.ones_like(height_map)

    norm = np.sqrt(dx**2 + dy**2 + dz**2)
    dx /= norm
    dy /= norm
    dz /= norm

    r = ((dx + 1.0) * 0.5 * 255).astype(np.uint8)
    g = ((dy + 1.0) * 0.5 * 255).astype(np.uint8)
    b = ((dz + 1.0) * 0.5 * 255).astype(np.uint8)
    normal_map = np.dstack((r, g, b))
    Image.fromarray(normal_map).save("cloud_normal.png")

    # 3. PACKED ORM MAP (Red = Ambient Occlusion, Green = Roughness, Blue = Metallic)
    print("Creating packed ORM map...")
    ao = ((1.0 - height_map * 0.4) * 255).astype(np.uint8)
    roughness = (np.ones_like(height_map) * 255).astype(np.uint8) # Fully matte rough clouds
    metallic = np.zeros_like(height_map, dtype=np.uint8)

    orm_map = np.dstack((ao, roughness, metallic))
    Image.fromarray(orm_map).save("cloud_orm.png")

    print(f"[SUCCESS] All PBR cloud maps exported successfully at {size}x{size}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procedural PBR Cloud Texture Map Generator")
    parser.add_argument(
        "resolution",
        type=str,
        nargs="?",
        default="2k",
        choices=["1k", "2k", "4k"],
        help="Target export resolution: 1k (1024), 2k (2048), or 4k (4096). Default is 2k."
    )
    
    args = parser.parse_args()
    
    resolution_mapping = {
        "1k": 1024,
        "2k": 2048,
        "4k": 4096
    }
    
    target_size = resolution_mapping[args.resolution]
    create_cloud_pbr(target_size)
