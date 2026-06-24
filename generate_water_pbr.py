import argparse
import numpy as np
from PIL import Image

def generate_perlin_noise_2d(shape, res):
    """Generates seamless (tileable) 2D Perlin noise."""
    def f(t): return 6*t**5 - 15*t**4 + 10*t**3

    x = np.linspace(0, res, shape, endpoint=False)
    y = np.linspace(0, res, shape, endpoint=False)
    x_grid, y_grid = np.meshgrid(x, y, indexing='ij')

    r0_x, r0_y = x_grid % 1.0, y_grid % 1.0
    r1_x, r1_y = r0_x - 1.0, r0_y - 1.0

    # Gradient grid
    gradients = np.random.randn(res, res, 2)
    # Normalize gradients to unit vectors for cleaner noise distribution
    norm = np.linalg.norm(gradients, axis=-1, keepdims=True)
    gradients = np.where(norm > 0, gradients / norm, gradients)

    i_x, i_y = (x_grid // 1).astype(int), (y_grid // 1).astype(int)

    # FIX: Use modulo (%) to wrap indices seamlessly around the boundaries
    i_x0 = i_x % res
    i_x1 = (i_x + 1) % res
    i_y0 = i_y % res
    i_y1 = (i_y + 1) % res

    n00 = gradients[i_x0, i_y0][..., 0] * r0_x + gradients[i_x0, i_y0][..., 1] * r0_y
    n10 = gradients[i_x1, i_y0][..., 0] * r1_x + gradients[i_x1, i_y0][..., 1] * r0_y
    n01 = gradients[i_x0, i_y1][..., 0] * r0_x + gradients[i_x0, i_y1][..., 1] * r1_y
    n11 = gradients[i_x1, i_y1][..., 0] * r1_x + gradients[i_x1, i_y1][..., 1] * r1_y

    t_x, t_y = f(r0_x), f(r0_y)
    return (n00 * (1.0 - t_x) + n10 * t_x) * (1.0 - t_y) + (n01 * (1.0 - t_x) + n11 * t_x) * t_y

def create_water_pbr(size=2048):
    print(f"Generating water textures at {size}x{size} resolution...")

    # Create fractal noise (multiple octaves)
    noise = (
        1.0 * generate_perlin_noise_2d(size, 8) +
        0.5 * generate_perlin_noise_2d(size, 16) +
        0.25 * generate_perlin_noise_2d(size, 32)
    )

    # Normalize values to range
    noise = (noise - noise.min()) / (noise.max() - noise.min())

    # CRITICAL STEP FOR WATER: Reshape noise into sharp caustic wave crests
    height_map = 1.0 - np.abs(noise - 0.5) * 2.0
    height_map = np.power(height_map, 1.5) # Sharpen wave peaks

    # 1. ALBEDO (Deep blue base with bright crest accents)
    print("Creating Albedo map...")
    albedo_r = (0.05 + height_map * 0.1) * 255
    albedo_g = (0.20 + height_map * 0.3) * 255
    albedo_b = (0.60 + height_map * 0.4) * 255
    albedo_rgb = np.dstack((albedo_r, albedo_g, albedo_b)).astype(np.uint8)
    Image.fromarray(albedo_rgb).save("water_albedo.png")

    # 2. NORMAL MAP (Surface wave ripples)
    print("Generating Normal map...")
    strength = 25.0  # Wave relief prominence intensity
    hx = np.roll(height_map, -1, axis=1) - np.roll(height_map, 1, axis=1)
    hy = np.roll(height_map, -1, axis=0) - np.roll(height_map, 1, axis=0)

    # Configured for Godot standard OpenGL format (+Y up, +X right)
    dx = -hx * strength
    dy = -hy * strength
    dz = np.ones_like(height_map)

    norm = np.sqrt(dx**2 + dy**2 + dz**2)
    r = ((dx / norm + 1.0) * 0.5 * 255).astype(np.uint8)
    g = ((dy / norm + 1.0) * 0.5 * 255).astype(np.uint8)
    b = ((dz / norm + 1.0) * 0.5 * 255).astype(np.uint8)
    normal_map = np.dstack((r, g, b))
    Image.fromarray(normal_map).save("water_normal.png")

    # 3. PACKED ORM MAP (R=Ambient Occlusion, G=Roughness, B=Metallic)
    print("Creating packed ORM map...")
    # Red Channel: Ambient Occlusion
    ao = ((1.0 - height_map * 0.1) * 255).astype(np.uint8)

    # Green Channel: Roughness (High values give the texture its distinct orange/yellow profile)
    roughness_values = 0.25 + (1.0 - height_map) * 0.15
    roughness = (roughness_values * 255).astype(np.uint8)
    roughness = np.clip(roughness, 60, 255)

    # Blue Channel: Metallic (Non-metallic surface = 0)
    metallic = np.zeros_like(height_map, dtype=np.uint8)

    orm_map = np.dstack((ao, roughness, metallic))
    Image.fromarray(orm_map).save("water_orm.png")

    # 4. DISPLACEMENT MAP (For Godot vertex shader wave tessellation)
    print("Creating Displacement map...")
    Image.fromarray((height_map * 255).astype(np.uint8)).save("water_displacement.png")

    print(f"[SUCCESS] All PBR water maps exported successfully at {size}x{size}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procedural PBR Water Texture Map Generator")
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
    create_water_pbr(target_size)
