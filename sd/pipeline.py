import torch 
import numpy as np 
import pandas as pd 
from tqdm import tqdm 
from ddpm import DDPMSampler 
import sd.clip
WIDTH = 512
HEIGHT = 512
LATENT_WIDTH = 64
LATENT_HEIGHT = 64

def generate(prompt :str, uncond_prompt: str, input_image=None,strength = 0.8, do_cfg = True, cfg_scale =7.5, sampler_name = "ddpm", n_inference_steps =50, models ={}, seed = None ,device = None, idle_device = None ,tokenizer=None ):
    with torch.no_grad():

        if not (0<strength<=1):
            raise ValueError("invalid rnage in strength")
        if idle_device:
            to_idle: lambda x: x.to(idle_device)
        else :
            to_idle: lambda x: x    

        generator = torch.Generator(device = device)
        if seed is None:
            generate.seed()
        else:
            generator.manual_seed(seed)
        clip = models["clip"]   
        clip.to(device)
             
        if do_cfg:
            cond_tokens = tokenizer.batch_encode_plus([prompt], padding = "max_length" , max_length = 77).input_ids
            cond_tokens = torch.tensor(cond_tokens , dtype = torch.long, devioce =device)
            cond_context = clip(cond_tokens)

            uncond_tokens = tokenizer.batch_encode_plus([uncond_prompt], padding= "max_length", max_length = 77).input_ids
            uncond_tokens = torch.tensor(uncond_tokens,dtype = torch.long , device = device )
            uncond_context = clip(uncond_tokens)

            context = torch.cat([cond_context , uncond_context])
        else:
            token = tokenizer.batch_encode_plus([prompt], padding = "max_length" , max_length = 77).input_ids
            tokens = torch.tensor(tokens, dtype= torch.long, device=device)

            context = clip(tokens)
        to_idle(clip)

        if sampler_name == "ddpm":
            sampler = DDPMSampler(generator)
            sampler.set_infere
        else:
            raise ValueError(f"invalid sapmler{sampler_name}")       
        latents_shape = (1,4,LATENT_HEIGHT, LATENT_WIDTH)

        if input_image:
            encoder = models["encoder"]
            encoder.to(device)

            input_image_tensor = input_image.resize((WIDTH,HEIGHT))
            input_image_tensor = np.array(input_image_tensor)
            input_image_tensor = torch.tensor(input_image_tensor, dtype =torch.float32)
            input_image_tensor = rescale(input_image_tensor, (0,255),(-1,1))
            input_image_tensor = input_image_tensor.unsqueeze(0)
            input_image_tensor = input_image_tensor.permute(0,3,1,2)
            
            encoder_noise = torch.randn(latents_shape, genrator = generator, device = device,)
            latents = encoder(input_image_tensor, encoder_noise )

            sampler.set_strength(strength=strength) 
            latents = sampler.add_noise(latents, sampler.timesteps[0])

            to_idle(encoder)
        else:
            
            latents = torch.randn(latents_shape, generator=generator, device=device  ) 

            diffusion = models["diffusion"]
            diffusion.to(device)

            timesteps = tqdm(sampler.timesteps)
            for i, timestep in enumerate(timesteps):
                time_embedding = get_time_embedding(timestep).to

                modle_input = latents
                if do_cfg :
                    modle_input = modle_input.repeat(2,1,1,1)
                modle_output = diffusion(modle_input, context, time_embedding)#predicted nois 

                if do_cfg:
                    output_cond , output_uncond = modle_output.chunk(2)
                if do_cfg:
                    modle_output = cfg_scale*(output_cond - output_uncond) + output_uncond
                latents = sampler.step(timestep, latents,modle_output  )
            to_idle(diffusion )
            decoder = models["decoder"]
            decoder.to(device)
            images = decoder(latents)
            to_idle(decoder)

            images = rescale(images, (-1,1), (0,255), clamp = True)

            images = images.permute(0,2,3,1)
            images  = images.to("cpu" , torch.uint8).numpy()
            return images[0]            
        
    def rescale(x, old_range , new_range,clamp = True) :
        old_min, old_max = old_range 
        new_min, new_max = new_range 
        x -= old_min 
        x *= (new_max - new_min)/(old_max - old_min )
        x += new_min 
        if clamp :
            x = x.clamp(new_min , new_max)
        return x 
    def get_time_embedding(timestep):
        freqs = torch.pow(10000, -torch.arange(start=0,end=160, dtype=torch.float32)/160)
        x = torch.tensor([timestep], dtype=torch.float32)[:, None] * freqs[None]
        return torch.cat([torch.cos(x)])


