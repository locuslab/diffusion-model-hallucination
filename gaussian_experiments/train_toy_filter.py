import numpy as np
import os
import random
import torch
from ddpm_torch.toy import *
from ddpm_torch.utils import seed_all, infer_range
from torch.optim import Adam, lr_scheduler
from matplotlib import pyplot as plt
from argparse import ArgumentParser
import wandb

def parse_arguments():

    parser = ArgumentParser()

    parser.add_argument("--dataset", choices=["gaussian1d", "gaussian8", "gaussian25", "swissroll", 
                                               "gaussian25_rotated"], default="gaussian25")
    parser.add_argument("--size", default=100000, type=int)
    parser.add_argument("--root", default="~/datasets", type=str, help="root directory of datasets")
    parser.add_argument("--epochs", default=300, type=int, help="total number of training epochs")
    parser.add_argument("--lr", default=0.001, type=float, help="learning rate")
    parser.add_argument("--beta1", default=0.9, type=float, help="beta_1 in Adam")
    parser.add_argument("--beta2", default=0.999, type=float, help="beta_2 in Adam")
    parser.add_argument("--lr-warmup", default=0, type=int, help="number of warming-up epochs")
    parser.add_argument("--batch-size", default=10000, type=int)
    parser.add_argument("--timesteps", default=1000, type=int, help="number of diffusion steps")

    parser.add_argument("--beta-schedule", choices=["quad", "linear", "warmup10", "warmup50", "jsd"], default="linear") 
    parser.add_argument("--beta-start", default=0.001, type=float)
    parser.add_argument("--beta-end", default=0.2, type=float)
    parser.add_argument("--model-mean-type", choices=["mean", "x_0", "eps"], default="eps", type=str)
    parser.add_argument("--model-var-type", choices=["learned", "fixed-small", "fixed-large"], default="fixed-large", type=str)  # noqa
    parser.add_argument("--loss-type", choices=["kl", "mse"], default="mse", type=str)
    parser.add_argument("--image-dir", default="./images/train", type=str)
    parser.add_argument("--exp_str", default="0", type=str)
    parser.add_argument("--chkpt-dir", default="./chkpts", type=str)
    parser.add_argument("--chkpt-intv", default=100, type=int, help="frequency of saving a checkpoint")
    parser.add_argument("--eval-intv", default=10, type=int)
    parser.add_argument("--seed", default=1234, type=int, help="random seed")
    parser.add_argument("--resume", action="store_true", help="to resume training from a checkpoint")
    parser.add_argument("--device", default="cuda:0", type=str)
    parser.add_argument("--mid-features", default=128, type=int)
    parser.add_argument("--num-temporal-layers", default=3, type=int)

    parser.add_argument('--num_modes', type=int, help='Number of Modes (for 1D only)', default=3)
    parser.add_argument('--modes', type=int, nargs='+', help='Means of the Gaussians (for 1D only)', default=[1, 2, 3])
 
    parser.add_argument("--generations", default=1, type=int)
    parser.add_argument("--num_sample_images", default=10_000_000, type=int)
    
    parser.add_argument("--filter_type", default="random", type=str)
    parser.add_argument("--start_timestep_var", default=10, type=int)

    parser.add_argument("--wandb_project_name", default="synthetic", type=str)
    parser.add_argument("--wandb_entity", default="cmu-research", type=str)
    parser.add_argument("--log_results", action="store_true", help="log results to wandb")

    args = parser.parse_args()
    return args

def main():

    args = parse_arguments()
    assert args.num_modes == len(args.modes) # Number of modes should be equal to the number of means.

    if "1d" in args.dataset:
        dataset_name = args.dataset + f"_{args.num_modes}_" + "".join([str(mode) for mode in args.modes])
    else:
        dataset_name = args.dataset
    args.store_name = "_".join([
        dataset_name, str(args.size), "g",str(args.generations),"e",str(args.epochs), f"t{args.timesteps}", f"m{args.mid_features}",
        f"nl{args.num_temporal_layers}", f"b{args.beta_schedule}", 'filter', args.filter_type,
        f"seed{args.seed}", args.exp_str
    ])
    # set seed
    seed_all(args.seed)
    print(args)

    if args.log_results:
        wandb.init(project=args.wandb_project_name,
                                   entity=args.wandb_entity, name=args.store_name)
        wandb.config.update(args)
        wandb.run.log_code(".")


    # prepare toy data
    in_features = 1 if "1d" in args.dataset else 2
    dataset = args.dataset
    data_size = args.size
    root = os.path.expanduser(args.root)
    batch_size = args.batch_size
    num_batches = data_size // batch_size
    chkpt_dir = args.chkpt_dir + f"/{args.store_name}"
    if not os.path.exists(chkpt_dir):
        os.makedirs(chkpt_dir)

    for gen in range(args.generations): 
        if args.log_results:
            wandb.log({'gen':gen})
        print("Generation: ", gen)
        if gen==0:
            trainloader = DataStreamer(dataset, batch_size=batch_size, num_batches=num_batches, modes=args.modes)
            print("Max and Min of dataset: ", np.max(trainloader.dataset.data), np.min(trainloader.dataset.data))
            np.save(f"{chkpt_dir}/real_dataset.npy", trainloader.dataset.data)
        else:
            if os.path.exists(f"{args.chkpt_dir}/{args.store_name}/gen_dataset_{gen-1}_filtered.npy"):
                dataset_gen = np.load(f"{args.chkpt_dir}/{args.store_name}/gen_dataset_{gen-1}_filtered.npy")
            else:
                print('Filtered does not exist!!!!')
                dataset_gen = np.load(f"{args.chkpt_dir}/{args.store_name}/gen_dataset_{gen-1}.npy")
            print("Dataset Gen: ", dataset_gen.shape)
            trainloader = DataStreamer(dataset_gen, batch_size=batch_size, num_batches=num_batches, modes=args.modes)

        # training parameters
        device = torch.device(args.device)
        epochs = args.epochs

        # diffusion parameters
        beta_schedule = args.beta_schedule
        beta_start, beta_end = args.beta_start, args.beta_end
        timesteps = args.timesteps
        betas = get_beta_schedule(
            beta_schedule, beta_start=beta_start, beta_end=beta_end, timesteps=timesteps)
        model_mean_type = args.model_mean_type
        model_var_type = args.model_var_type
        loss_type = args.loss_type
        diffusion = GaussianDiffusion(
            betas=betas, model_mean_type=model_mean_type, model_var_type=model_var_type, loss_type=loss_type)

        # model parameters
        out_features = 2 * in_features if model_var_type == "learned" else in_features
        mid_features = args.mid_features
        model = Decoder(in_features, mid_features, args.num_temporal_layers)
        model.to(device)

        # training parameters
        lr = args.lr
        beta1, beta2 = args.beta1, args.beta2
        optimizer = Adam(model.parameters(), lr=lr, betas=(beta1, beta2))

        # checkpoint path
        chkpt_dir = args.chkpt_dir + f"/{args.store_name}"
        if not os.path.exists(chkpt_dir):
            os.makedirs(chkpt_dir)
        chkpt_path = os.path.join(chkpt_dir, f"ddpm_{dataset}_gen_{gen}.pt")

        # set up image directory
        image_dir = os.path.join(args.image_dir, f"{dataset}", args.store_name)
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        # scheduler
        warmup = args.lr_warmup
        scheduler = lr_scheduler.LambdaLR(
            optimizer, lr_lambda=lambda t: min((t + 1) / warmup, 1.0)) if warmup > 0 else None

        # load trainer
        grad_norm = 0  # gradient global clipping is disabled
        eval_intv = args.eval_intv
        chkpt_intv = args.chkpt_intv
        trainer = Trainer(
            model=model,
            optimizer=optimizer,
            diffusion=diffusion,
            epochs=epochs,
            trainloader=trainloader,
            scheduler=scheduler,
            grad_norm=grad_norm,
            device=device,
            eval_intv=eval_intv,
            chkpt_intv=chkpt_intv, gen=gen,args=args
        )

        print("Len of trainloader: ", len(trainloader))
        print("Data size: ", data_size)
        plt.figure(figsize=(6, 6))
        dataloader_dataset = trainloader.dataset
        if in_features==1:
            # Visualize histogram in case of 1D input.
            # Set log scale
            plt.yscale("log")
            plt.hist(dataloader_dataset.data, bins=100, alpha=0.7, edgecolor='black')
        else:
            plt.scatter(*np.hsplit(dataloader_dataset.data, 2), s=0.5, alpha=0.7)
        plt.tight_layout()
        plt.savefig(f"{image_dir}/gen_{gen}.jpg")
        plt.close()


        # max_eval_count = min(data_size, 30000)
        max_eval_count = max(args.num_sample_images, data_size)#min(data_size, data_size)
        print("Max eval count: ", max_eval_count)
        # eval_batch_size = min(max_eval_count, 30000)
        eval_batch_size = min(max_eval_count, 1_000_000)
        print("Eval batch size: ", eval_batch_size)
        xlim, ylim = infer_range(trainloader.dataset)
        value_range = (xlim, ylim)
        true_data = iter(trainloader)
        if in_features==1:
            evaluator = Evaluator1D(
                true_data=np.concatenate([
                    next(true_data) for _ in range(min(max_eval_count // eval_batch_size, args.size//args.batch_size))
                ]), eval_batch_size=eval_batch_size, max_eval_count=max_eval_count, value_range=value_range)
        else:
            evaluator = Evaluator(
                true_data=np.concatenate([
                    next(true_data) for _ in range(max_eval_count // eval_batch_size)
                ]), eval_batch_size=eval_batch_size, max_eval_count=max_eval_count, value_range=value_range)
        if args.resume:
            try:
                trainer.load_checkpoint(chkpt_path)
            except FileNotFoundError:
                print("Checkpoint file does not exist!")
                print("Starting from scratch...")

        gen_dataset = trainer.train(evaluator, chkpt_path=chkpt_path, image_dir=image_dir, xlim=xlim, ylim=ylim)
        np.save(f"{chkpt_dir}/gen_dataset_{gen}.npy", gen_dataset)
        print(gen_dataset.shape)
        if "1d" in args.dataset:
            # Set log scale
            plt.yscale("log")
            plt.hist(gen_dataset, bins=100, alpha=0.7, edgecolor='black')
        else:
            plt.scatter(*np.hsplit(gen_dataset, 2), s=0.5, alpha=0.7)
        plt.tight_layout()
        plt.savefig(f"{chkpt_dir}/generated_{gen}.png")
        plt.close()

        if args.log_results:
            wandb.log({f"Gen": wandb.Image(f"{chkpt_dir}/generated_{gen}.png", caption=f"Gen {gen + 1}")})

        def custom_sample_fn(n, model, diffusion, shape , device='cuda'):
            shape = (n,) + shape
            sample, noise, _, pred_x0 = diffusion.p_sample_save_all(
                denoise_fn=model, shape=shape, device=device, noise=None)
            return sample.cpu().numpy(), noise, pred_x0
        number_of_samples = data_size + 2500
        if "1d" in args.dataset:
            shape = (1,)
        else:
            shape = (2, )
        device = args.device
        x_gen = []
        all_predx0 = []

        for j in range(0, number_of_samples, eval_batch_size):
            sample, _, pred_x0 = custom_sample_fn(eval_batch_size, model, diffusion, shape, device=device)
            x_gen.extend(sample)
            if "1d" in dataset:
                pred_x0_arr = np.array(pred_x0).transpose(1, 0, 2).reshape(eval_batch_size, 1000)
            else:
                pred_x0_arr = np.array(pred_x0).transpose(1, 0, 2)
            all_predx0.extend(pred_x0_arr)
        x_gen = np.array(x_gen)[:number_of_samples]
        all_predx0 = np.array(all_predx0)[:number_of_samples]
        np.save(f"{chkpt_dir}/gen_dataset_{gen}_predx0.npy", all_predx0)
        np.save(f"{chkpt_dir}/gen_dataset_{gen}_xgen.npy", x_gen)
        print("Generated samples: ", x_gen.shape)
        print("Filtering!")
        if args.filter_type=="variance":
            start_timestep = args.start_timestep_var
            # end_timestep = 100
            if "1d" in dataset:
                variance = np.var(all_predx0[:, -start_timestep:], axis=1)
            else:
                variance = np.mean(np.var(all_predx0[:, -start_timestep:, ], axis=1), axis=1)
            # Sort the variance
            sorted_indices = np.argsort(variance)
            # Get k samples from the sorted indices
            filtered_samples = x_gen[sorted_indices[:data_size]]
        elif args.filter_type=="random":
            random_indices = random.sample(range(len(x_gen)), data_size)
            filtered_samples = x_gen[random_indices]

        print("Filtered samples: ", filtered_samples.shape)
        np.save(f"{chkpt_dir}/gen_dataset_{gen}_filtered.npy", filtered_samples)
        if "1d" in args.dataset:
            # Set log scale
            plt.yscale("log")
            plt.hist(filtered_samples, bins=100, alpha=0.7, edgecolor='black')
        else:
            plt.scatter(*np.hsplit(filtered_samples, 2), s=0.5, alpha=0.7)
        plt.tight_layout()
        plt.savefig(f"{chkpt_dir}/generated_filtered_{gen}.png")
        plt.close()

        if "1d" in args.dataset:
            # Set log scale
            plt.yscale("log")
            plt.hist(x_gen, bins=100, alpha=0.7, edgecolor='black')
        else:
            plt.scatter(*np.hsplit(x_gen, 2), s=0.5, alpha=0.7)
        plt.tight_layout()
        plt.savefig(f"{chkpt_dir}/generated_unfiltered_{gen}.png")
        plt.close()


        if args.log_results:
            wandb.log({f"Gen": wandb.Image(f"{chkpt_dir}/generated_{gen}.png", caption=f"Gen {gen + 1}")})
            wandb.log({f"f_Gen": wandb.Image(f"{chkpt_dir}/generated_filtered_{gen}.png", caption=f"Filtered Gen {gen + 1}")})
            wandb.log({f"uf_Gen": wandb.Image(f"{chkpt_dir}/generated_unfiltered_{gen}.png", caption=f"Unfiltered Gen {gen + 1}")})


if __name__ == "__main__":
    main()