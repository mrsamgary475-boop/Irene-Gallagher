import argparse
import json
import shutil
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import torch
from PIL import Image
from rembg import remove
from transformers import pipeline


def build_asset(source_path: Path, output_dir: Path, max_dim: int = 1024):
    source = Image.open(source_path).convert("RGB")
    scale = min(1.0, max_dim / max(source.size))
    if scale < 1:
        source = source.resize(
            (round(source.width * scale), round(source.height * scale)),
            Image.Resampling.LANCZOS,
        )
    width, height = source.size

    print("Creating AI subject cutout...")
    subject_rgba = remove(source)
    if subject_rgba.mode != "RGBA":
        subject_rgba = subject_rgba.convert("RGBA")
    source_rgba = np.array(subject_rgba)
    alpha = np.array(subject_rgba.getchannel("A"))

    print("Estimating depth...")
    depth_pipe = pipeline(
        "depth-estimation",
        model="depth-anything/Depth-Anything-V2-Small-hf",
        device=0 if torch.cuda.is_available() else -1,
    )
    depth_image = depth_pipe(source)["depth"].resize((width, height), Image.Resampling.BILINEAR)
    depth = np.array(depth_image).astype(np.float32)
    depth = ((depth - depth.min()) / max(depth.max() - depth.min(), 1e-6) * 255).astype(np.uint8)

    print("Detecting body joints...")
    mp_pose = mp.solutions.pose
    with mp_pose.Pose(static_image_mode=True, model_complexity=1, enable_segmentation=False) as pose:
        pose_result = pose.process(np.array(source))
    if not pose_result.pose_landmarks:
        raise RuntimeError("No full-body pose was detected in the source photo.")

    landmarks = pose_result.pose_landmarks.landmark

    def xy(index):
        point = landmarks[index]
        return (
            int(np.clip(point.x, 0, 1) * (width - 1)),
            int(np.clip(point.y, 0, 1) * (height - 1)),
        )

    def line_mask(pairs, thickness):
        mask = np.zeros((height, width), dtype=np.uint8)
        for first, second in pairs:
            first_point, second_point = xy(first), xy(second)
            cv2.line(mask, first_point, second_point, 255, thickness, cv2.LINE_AA)
            cv2.circle(mask, first_point, thickness // 2, 255, -1, cv2.LINE_AA)
            cv2.circle(mask, second_point, thickness // 2, 255, -1, cv2.LINE_AA)
        return mask

    body_width = max(24, int(abs(xy(11)[0] - xy(12)[0]) * 0.65))
    torso_points = np.array([xy(index) for index in (11, 12, 24, 23)], dtype=np.int32)
    torso_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(torso_mask, torso_points, 255)

    left_arm = line_mask([(11, 13), (13, 15)], max(12, body_width // 3))
    right_arm = line_mask([(12, 14), (14, 16)], max(12, body_width // 3))
    legs = line_mask([(23, 25), (25, 27), (24, 26), (26, 28)], max(16, body_width // 2))

    head_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(
        head_mask,
        xy(0),
        (max(18, body_width // 2), max(24, body_width * 2 // 3)),
        0,
        0,
        360,
        255,
        -1,
    )
    person_mask = torso_mask.copy()
    for layer_mask in (head_mask, left_arm, right_arm, legs):
        person_mask = cv2.bitwise_or(person_mask, layer_mask)
    person_mask = cv2.dilate(person_mask, np.ones((17, 17), dtype=np.uint8), iterations=1)
    person_mask = cv2.bitwise_and(person_mask, alpha)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    source_bgr = cv2.cvtColor(np.array(source), cv2.COLOR_RGB2BGR)
    subject_mask = person_mask
    background_bgr = cv2.inpaint(source_bgr, subject_mask, 7, cv2.INPAINT_TELEA)
    Image.fromarray(cv2.cvtColor(background_bgr, cv2.COLOR_BGR2RGB)).save(output_dir / "background.png")

    def save_layer(name, mask):
        layer = source_rgba.copy()
        layer[:, :, 3] = cv2.bitwise_and(mask, person_mask)
        Image.fromarray(layer).save(output_dir / name)

    source_rgba[:, :, 3] = person_mask
    Image.fromarray(source_rgba).save(output_dir / "subject.png")
    save_layer("torso.png", torso_mask)
    save_layer("head.png", head_mask)
    save_layer("left_arm.png", left_arm)
    save_layer("right_arm.png", right_arm)
    save_layer("legs.png", legs)
    Image.fromarray(depth).save(output_dir / "depth.png")
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "width": width,
                "height": height,
                "source_model": "rembg + Depth-Anything-V2-Small + MediaPipe Pose",
                "layers": [
                    "background.png",
                    "subject.png",
                    "torso.png",
                    "head.png",
                    "left_arm.png",
                    "right_arm.png",
                    "legs.png",
                    "depth.png",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Created 2.5D asset in {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Irene's AI-assisted 2.5D avatar layers.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("avatar/live/irene_photo.png"),
        help="Source photo path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("avatar/live/irene_2p5d"),
        help="Output asset directory.",
    )
    args = parser.parse_args()
    build_asset(args.source, args.output)
