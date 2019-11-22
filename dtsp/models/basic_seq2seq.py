# encoding: utf-8
"""
@author : zhirui zhou
@contact: evilpsycho42@gmail.com
@time   : 2019/11/19 14:12
"""
import torch.nn as nn
from torch import optim
import torch
import random

from dtsp.modules import BasicRNNEncoder, BasicRNNDecoder
import pytorch_lightning as pl


class BasicSeq2Seq(pl.LightningModule):

    def __init__(self, hparams):
        super(BasicSeq2Seq, self).__init__()
        self.hparams = hparams
        self.loss_fn = nn.MSELoss()
        self.encoder = BasicRNNEncoder(**hparams)
        self.decoder = BasicRNNDecoder(**hparams)

    def forward(self, enc_seqs, n_step):
        _, hidden = self.encoder(enc_seqs)
        inputs = enc_seqs[:, -1].unsqueeze(1)
        outputs = []
        for i in range(n_step):
            inputs, hidden = self.decoder(inputs, hidden)
            outputs.append(inputs)
        return torch.cat(outputs, dim=1)

    def training_step(self, batch, batch_nb):
        enc_inputs = batch['enc_inputs']
        dec_inputs = batch['dec_inputs']
        dec_outputs = batch['dec_outputs']

        outputs = []
        _, hidden = self.encoder(enc_inputs)
        dec_inputs_i = dec_inputs[:, 0].unsqueeze(1)
        n_steps = dec_outputs.shape[1]
        for i in range(n_steps):
            output, hidden = self.decoder(dec_inputs_i, hidden)
            outputs.append(output)
            if random.random() < self.hparams['teacher_forcing_rate']:
                dec_inputs_i = dec_inputs[:, i].unsqueeze(1)
            else:
                dec_inputs_i = output
        outputs = torch.cat(outputs, dim=1)
        loss = self.loss_fn(outputs, dec_outputs)

        return {'loss': loss, 'log': {'train_loss': loss}}

    def validation_step(self, batch, batch_nb):
        enc_inputs = batch['enc_inputs']
        dec_outputs = batch['dec_outputs']
        n_step = dec_outputs.shape[1]
        pred_outputs = self(enc_inputs, n_step)
        loss = self.loss_fn(pred_outputs, dec_outputs)
        return {'val_loss': loss}

    def validation_end(self, outputs):
        loss_mean = 0

        for output in outputs:
            loss_mean += output['val_loss']
        log = {'val_loss': loss_mean / len(outputs)}
        return {'progress_bar': log, 'log': log}

    def configure_optimizers(self):
        return getattr(optim, self.hparams['optimizer'])(self.parameters(), lr=self.hparams['lr'])

    @pl.data_loader
    def train_dataloader(self):
        return self.hparams.get('train_dataloader')

    @pl.data_loader
    def val_dataloader(self):
        return self.hparams.get('valid_dataloader')

    @pl.data_loader
    def test_dataloader(self):
        return self.hparams.get('test_dataloader')
