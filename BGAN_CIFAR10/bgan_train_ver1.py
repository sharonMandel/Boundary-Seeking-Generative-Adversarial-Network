from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import sys
import time

import bgan_model as bgan

sys.path.append('../')
import image_utils as iu
from datasets import MNISTDataSet as DataSet
from datasets import DataIterator
from datasets import CiFarDataSet as DataSet2

results = {
    'output': './gen_img/',
    'model': './model/BGAN-model.ckpt'
}

train_step = {
    'epochs': 100,
    'batch_size': 64,
    'global_step': 50001,
    'logging_interval': 500,

}

'''
train_step = {
    'global_step': 200001,
    'logging_interval': 1000,
}
'''
def main():
    start_time = time.time()  # Clocking start

    # MNIST Dataset load
    #mnist = DataSet(ds_path="D:/DataSet/mnist/").data

    # Loading Cifar-10 DataSet
    ds = DataSet2(height=32,
                 width=32,
                 channel=3,
                 ds_path="/media/shar/240A27640A2731EA/shared2/Awesome-GANs-master/BGAN/cifar/",
                 ds_name='cifar-10')

    ds_iter = DataIterator(x=iu.transform(ds.train_images, '127'),
                           y=ds.train_labels,
                           batch_size=train_step['batch_size'],
                           label_off=True)  # using label # maybe someday, i'll change this param's name

    # Generated image save
    test_images = iu.transform(ds.test_images[:100], inv_type='127')
    iu.save_images(test_images,
                   size=[10, 10],
                   image_path=results['output'] + 'sample.png',
                   inv_type='127')

    # GPU configure
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as s:
        # BGAN Model
        model = bgan.BGAN(s)

        # Initializing
        s.run(tf.global_variables_initializer())
        # Load model & Graph & Weights
        saved_global_step = 0

        ckpt = tf.train.get_checkpoint_state('./model/')
        if ckpt and ckpt.model_checkpoint_path:
            # Restores from checkpoint
            model.saver.restore(s, ckpt.model_checkpoint_path)


            saved_global_step = int(ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1])
            print("[+] global step : %d" % saved_global_step, " successfully loaded")
        else:
            print('[-] No checkpoint file found')

        d_loss = 0.
        d_overpowered = False
        global_step = saved_global_step
        start_epoch = global_step // (len(ds.train_images) // model.batch_size)           # recover n_epoch
        ds_iter.pointer = saved_global_step % (len(ds.train_images) // model.batch_size)  # recover n_iter
        for epoch in range(start_epoch, train_step['epochs']):

            #batch_x, _ = mnist.train.next_batch(model.batch_size)
            batch_x, _ = ds_iter.next_batch()
            batch_x = batch_x.reshape(-1, model.n_input)
            batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

            # Update D network
            if not d_overpowered:
                _, d_loss = s.run([model.d_op, model.d_loss],
                                  feed_dict={
                                      model.x: batch_x,
                                      model.z: batch_z,
                                  })

            # Update G network
            _, g_loss = s.run([model.g_op, model.g_loss],
                              feed_dict={
                                  model.x: batch_x,
                                  model.z: batch_z,
                              })
            # Generated image save
            iu.save_images(samples,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir,
                               inv_type='127')

            d_overpowered = d_loss < g_loss / 2.
            # Logging
            if global_step % train_step['logging_interval'] == 0:
                batch_x, _ = ds_iter.next_batch()
                batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

                d_loss, g_loss, summary = s.run([model.d_loss, model.g_loss, model.merged],
                                                feed_dict={
                                                    model.x: batch_x,
                                                    model.z: batch_z,
                                                })

                # Print loss
                print("[+] Step %08d => " % global_step,
                      " D loss : {:.8f}".format(d_loss),
                      " G loss : {:.8f}".format(g_loss))

                # Training G model with sample image and noise
                sample_z = np.random.uniform(-1., 1., [model.sample_num, model.z_dim]).astype(np.float32)
                samples = s.run(model.g,
                                feed_dict={
                                    model.z: sample_z,
                                })

                samples = np.reshape(samples, [-1] + model.image_shape[1:])

                # Summary saver
                model.writer.add_summary(summary, global_step)

                # Export image generated by model G
                sample_image_height = model.sample_size
                sample_image_width = model.sample_size
                sample_dir = results['output'] + 'train_1{:08d}.png'.format(global_step)
                
                # Generated image save
                iu.save_images(samples,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir,
                               inv_type='127')

                # Model save
                model.saver.save(s, results['model'], global_step=global_step)
                print(sample_dir)
            global_step += 1
    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))
   
    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()

