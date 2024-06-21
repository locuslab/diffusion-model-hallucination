# Gaussian Experiments

This folder consists of the code to reproduce the results of 1D and 2D Gaussian experiments.

## Usage

### Training

To start training, you can use the `train_toy.py` script. Below is an example command to run an experiment on 1D Gaussian with 3 modes:

```sh
python train_toy.py --dataset gaussian1d --modes 1 2 3 --size 50000 --wandb_project_name synthetic --wandb_entity cmu-research --epochs 10000 --exp_str code_release_test --eval-intv 5000 --log_results --timesteps 1000 --generations 1
```

More examples are present in `run.sh`

### Primary Arguments

- `--dataset`: Choice of dataset (`gaussian1d`, `gaussian25`, `gaussian25_rotated`)
- `--size`: Size of the dataset (Number of Samples)
- `--epochs`: Total number of training epochs
- `--batch-size`: Batch size for training
- `--timesteps`: Number of diffusion steps (T)
- `--num_modes`: Number of modes (for 1D only)
- `--modes`: Means of the Gaussians (for 1D only)
- `--generations`: Number of generations for recursive training
- `--num_sample_images`: Number of images to sample from the diffusion model.
- `--exp_str`: Experiment string identifier
- `--wandb_project_name`: Name of the Weights & Biases project
- `--wandb_entity`: Weights & Biases entity
- `--log_results`: Log results to Weights & Biases


### Dataset Choices

- `gaussian1d`: 1D Gaussian distribution.
- `gaussian25`: 25-component Gaussian mixture in 2D.
- `gaussian25_rotated`: Rotated 25-component Gaussian mixture in 2D.

## Acknowledgements

This codebase builds upon the implementation provided in the [ddpm-torch repository](https://github.com/tqch/ddpm-torch). We are grateful to the authors for making their code publicly available.
