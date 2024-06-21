#!/bin/bash

# Change the following to your own project name and entity
WANDB_PROJECT_NAME="synthetic"
WANDB_ENTITY="cmu-research"

# 1D Mixture of Gaussian with 3 modes (1, 2, 3) with 20k samples
python train_toy.py \
    --dataset gaussian1d --modes 1 2 3 --size 20000 \
    --wandb_project_name $WANDB_PROJECT_NAME --wandb_entity $WANDB_ENTITY \
    --epochs 10000 --exp_str code_release --eval-intv 5000 --log_results --timesteps 1000 --generations 1

# 1D Mixture of Gaussian with 4 modes (1, 2, 4, 5) with 50k samples
python train_toy.py \
    --dataset gaussian1d --modes 1 2 4 5 --num_modes 4 --size 50000 \
    --wandb_project_name $WANDB_PROJECT_NAME --wandb_entity $WANDB_ENTITY \
    --epochs 10000 --exp_str code_release --eval-intv 5000 --log_results --timesteps 1000 --generations 1

# 2D Mixture of Gaussian with 25 modes and 100k samples (No filtering)
python train_toy.py \
    --dataset gaussian25 --size 100_000 \
    --wandb_project_name $WANDB_PROJECT_NAME --wandb_entity $WANDB_ENTITY \
    --epochs 10000 --exp_str code_release --eval-intv 5000 --log_results --timesteps 1000 \
    --num_sample_images 100_000 --batch-size 10000 --generations 5


# 2D Mixture of Gaussian with 25 modes and 100k samples and filter by variance trajectory
python train_toy_filter.py \
    --dataset gaussian25 --size 100_000 \
    --wandb_project_name $WANDB_PROJECT_NAME --wandb_entity $WANDB_ENTITY \
    --epochs 10000 --exp_str code_release --eval-intv 5000 --log_results --timesteps 1000 \
    --num_sample_images 500_000 --batch-size 10000 --generations 5 --filter_type "variance"

# 2D Mixture of Gaussian with 25 modes and 100k samples and filter by variance trajectory
python train_toy_filter.py \
    --dataset gaussian25 --size 100_000 \
    --wandb_project_name $WANDB_PROJECT_NAME --wandb_entity $WANDB_ENTITY \
    --epochs 10000 --exp_str code_release --eval-intv 5000 --log_results --timesteps 1000 \
    --num_sample_images 500_000 --batch-size 10000 --generations 5 --filter_type "random"