import io
import os
from PIL import Image
import numpy as np
import time
import math
import matplotlib.pyplot as plt
import csv

from scipy.stats import pearsonr
import pandas

import argparse
import torch
import torch.optim as optim
from torchvision import transforms
from torch.autograd import Variable

from valencenet import ValenceNet
from dataset import ValenceDataLoader

USE_CUDA = torch.cuda.is_available()
FLOAT = torch.cuda.FloatTensor if torch.cuda.is_available() else torch.FloatTensor
K = 100.

def to_tensor(ndarray, volatile=False, requires_grad=False, dtype=FLOAT):
    return Variable(
        torch.from_numpy(ndarray), volatile=volatile, requires_grad=requires_grad
    ).type(dtype)

def train_model(model, train_loader, criterion, optimizer, epoch, batch_size, trajectory_length):
    model.train()
    model.training = True

    # switch to train mode
    total = 0
    running_loss = 0
    for batch_idx, (features_stacked, valences) in enumerate(train_loader):
        if USE_CUDA:
            features_stacked, valences = features_stacked.cuda(), valences.cuda()
#        features_stacked = features_stacked.permute(1, 0, 2, 3, 4)
        features_stacked, valences = Variable(features_stacked).type(FLOAT), Variable(valences).type(FLOAT)

        current_batch_size = valences.size(0)
        model.reset_hidden_states(size=current_batch_size, zero=True)
        estimated_valences = model(features_stacked)
        estimated_valences = estimated_valences.view(-1)
        valences = valences.view(-1)
        # print (estimated_valences.shape)
        # print (valences.shape)
        loss = criterion(estimated_valences, valences)

        # compute gradient and do optimizer step
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        total += valences.size(0)

    epoch_loss = (float(running_loss) / float(total)) * 100.0
    print('{} MSELoss: {:.4f}'.format(
           'train', epoch_loss))

def train(model, datapath, subject_id, checkpoint_path, epochs, trajectory_length, args):
    mean_valences = 0
    db = ValenceDataLoader(datapath=datapath, subject_id=subject_id, trajectory_length=1)
    for _, valences in db:
        mean_valences += valences
    mean_valences /= len(db)
    # # TODO: cancel mean_valences
    # mean_valences = 0

    kwargs = {'num_workers': 1, 'pin_memory': True} if torch.cuda.is_available() else {}
    train_loader = torch.utils.data.DataLoader(ValenceDataLoader(datapath, subject_id=subject_id, trajectory_length=trajectory_length, mean=mean_valences), batch_size=args.bsize, shuffle=True, drop_last=True, **kwargs)

    criterion = torch.nn.MSELoss()
    optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=args.weight_decay)
    for epoch in range(1, epochs + 1):
        # train for one epoch
        train_model(model, train_loader, criterion, optimizer, epoch, args.bsize, trajectory_length)
#        # evaluate on validation set
        eval(model, datapath, subject_id, trajectory_length)
#
#        # remember best acc and save checkpoint
#        is_best = acc > best_acc
#        best_acc = max(acc, best_acc)
        state = {
            'epoch': epoch + 1,
            'state_dict': model.state_dict(),
        }
        torch.save(state, os.path.join(checkpoint_path, "checkpoint_{}.pth".format(epoch)))

def eval_model(model, eval_loader, batch_size, trajectory_length):
    total = 0
    predictions = []
    ground_truth = []
    features = []
    for batch_idx, (features_stacked, valences) in enumerate(eval_loader):
        if USE_CUDA:
            features_stacked, valences = features_stacked.cuda(), valences.cuda()
        features_stacked, valences = Variable(features_stacked).type(FLOAT), Variable(valences).type(FLOAT)

        current_batch_size = valences.size(0)
        model.reset_hidden_states(size=current_batch_size, zero=True)
        estimated_valences = model(features_stacked)
        estimated_valences = estimated_valences.view(-1)
        valences = valences.view(-1)

        if (estimated_valences.size(0) > batch_size):
            estimated_valences = estimated_valences[-batch_size:]
            valences = valences[-batch_size:]
            features_stacked = features_stacked[-batch_size:]

        # print (estimated_valences)

        for i in range(valences.size(0)):
            predictions.append(estimated_valences[i].item())
            ground_truth.append(valences[i].item())
            features.append(features_stacked[0,-1,].data.cpu().numpy())

    # with open('output.csv','w') as f:
    #     writer = csv.writer(f)
    #     predictions_2d = [[prediction] for prediction in predictions]
    #     writer.writerows(predictions_2d)

    CCC, _ = ccc(ground_truth, predictions)
    print ("ccc: {}".format(CCC))

    features = np.asarray(features)
    plt.clf()
    idx = range(len(predictions))
    plt.plot(idx, predictions, label = 'predictions', alpha = 0.7)
    plt.plot(idx, ground_truth, label = 'ground_truth', alpha = 0.7)
    plt.plot(idx, features[:,0], label = 'image_valence_mean', alpha = 0.2)
    plt.plot(idx, features[:,1], label = 'emo_watson', alpha = 0.2)
    plt.plot(idx, features[:,2], label = 'opensmile_valence', alpha = 0.2)
    plt.plot(idx, features[:,3], label = 'opensmile_arousal', alpha = 0.2)
    plt.plot(idx, features[:,4], label = 'polarity', alpha = 0.2)
    plt.plot(idx, features[:,5], label = 'both_laugh', alpha = 0.2)
    plt.legend()
    plt.pause(0.05)

def eval(model, datapath, subject_id, trajectory_length):
    model.eval()
    model.training = False

    kwargs = {'num_workers': 1, 'pin_memory': True} if torch.cuda.is_available() else {}
    eval_loader = torch.utils.data.DataLoader(ValenceDataLoader(datapath, subject_id=subject_id, trajectory_length=trajectory_length, test=True), batch_size=32, shuffle=False, **kwargs)
    return eval_model(model, eval_loader, 32, trajectory_length)

def mse(y_true, y_pred):
    from sklearn.metrics import mean_squared_error
    return mean_squared_error(y_true,y_pred)

def f1(y_true, y_pred):
    from sklearn.metrics import f1_score
    label = [0,1,2,3,4,5,6]
    return f1_score(y_true,y_pred,labels=label,average="micro")

def ccc(y_true, y_pred):
    true_mean = np.mean(y_true)
    true_variance = np.var(y_true)
    pred_mean = np.mean(y_pred)
    pred_variance = np.var(y_pred)

    rho,_ = pearsonr(y_pred,y_true)

    std_predictions = np.std(y_pred)

    std_gt = np.std(y_true)

    ccc = 2 * rho * std_gt * std_predictions / (std_predictions ** 2 + std_gt ** 2 + (pred_mean - true_mean) ** 2)

    return ccc, rho

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PyTorch on Place Recognition + Visual Odometry')

    parser.add_argument('--mode', default='train', type=str, help='support option: train/eval/test')
    parser.add_argument('--subject', default=1, type=int, help='subject_id')
    parser.add_argument('--datapath', default='data', type=str, help='path KITII odometry dataset')
    parser.add_argument('--bsize', default=32, type=int, help='minibatch size')
    parser.add_argument('--trajectory_length', default=10, type=int, help='trajectory length')
    parser.add_argument('--lr', type=float, default=0.01, metavar='LR', help='learning rate (default: 0.0001)')
    parser.add_argument('--momentum', type=float, default=0.5, metavar='M', help='SGD momentum (default: 0.5)')
    parser.add_argument('--weight_decay', type=float, default=1e-4, metavar='M', help='SGD momentum (default: 0.5)')
    parser.add_argument('--tau', default=0.001, type=float, help='moving average for target network')
    parser.add_argument('--debug', dest='debug', action='store_true')
    parser.add_argument('--train_iter', default=20000000, type=int, help='train iters each timestep')
    parser.add_argument('--epsilon', default=50000, type=int, help='linear decay of exploration policy')
    parser.add_argument('--checkpoint_path', default='checkpoints/', type=str, help='Checkpoint path')
    parser.add_argument('--checkpoint', default=None, type=str, help='Checkpoint')
    args = parser.parse_args()

    model = ValenceNet(lstm_enabled=False)
    if args.checkpoint is not None:
        checkpoint = torch.load(args.checkpoint)
        model.load_state_dict(checkpoint['state_dict'])
    if USE_CUDA:
        model.cuda()

    args = parser.parse_args()
    if args.mode == 'train':
        train(model, args.datapath, args.subject, args.checkpoint_path, args.train_iter, args.trajectory_length, args)
    elif args.mode == 'eval':
        eval(model, args.datapath, args.subject, args.trajectory_length)
    elif args.mode == 'test':
        eval(model, args.datapath, args.subject, args.trajectory_length)
    else:
        raise RuntimeError('undefined mode {}'.format(args.mode))

