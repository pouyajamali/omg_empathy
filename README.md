# omg_empathy
Code for paper: EmoCog Model for Multimodal Empathy Prediction

Submission to the OMG-Empathy Challenge 2019

Model 1 - Submission 1. Model 2 - Submission 2.

### Requirements

* `PyTorch`
* `OpenSMILE`
* `pip install -r requirements.txt `

### Data Processing
To get valence predictions on every frame and the mutual laughter frame number extract faces from video and run `python process_data.py` on trainset. For testset, run `python process_data_trainset.py`. 

Specific the file paths in both scripts:

`path = ./path/to/groundtruth/labels`

`img_path = ./path/to/face/images`

`save_path = ./path/to/save/valence/prediction`

`frame_path = ./path/to/save/mutual/laughter/frame/number`


### Model 1
To train the model, run `python train_svm.py`. Specify the file paths in the script to:

`path = ./path/to/final/features/csv/files(trainset)`

`savepath = ./path/to/save/svm/model`

To test the model, run `python test_svm.py`. Specify the file paths in the script to:

`path = ./path/to/final/features/csv/files(testset)`

`savepath = ./path/to/save/test/results`

`svmpath = ./path/to/saved/svm/models`

Processed features are provided in `./features_train/` and `./features_test/`.


### Model 2
Input desired file: `Subject_X_Story_X`

* [non-verbal features]
	- openSmile feature extraction tool [https://www.audeering.com/technology/opensmile/]
	- Emosic [https://arxiv.org/abs/1807.08775]
* [verbal features] 
	- tone analyzer (IBM watson) [https://tone-analyzer-demo.ng.bluemix.net/]	
	- TextBlob python API [https://textblob.readthedocs.io/en/dev/]

The audio of each video was extracted using ffmpeg[https://www.ffmpeg.org/].
`ffmpeg -i OMG_Empathy2019/Training/Videos/Subject_X_Story_X.mp4  -vn -acodec pcm_s16le -ar 16000 -ac 1 wav/Subject_X_Story_X.wav`
`Speech` folder consists of the text of each video alongside a csv file with time offset values (timestamps) for the beginning and end of each spoken word, using Speech-to-text Google API [https://cloud.google.com/speech-to-text/]

`$ bash preprocess/run.sh `
input desired file `Subject_X_Story_X`

To train a network (classifier, regression) based on the extracted features, in NN/classifier or NN/regression directory:
`python main.py --mode train --subject X`
`python main.py --mode test --subject X --story Y --checkpoint <path-to-checkpoint>`


### Result
**Test results on validation set:**

| Subject       | Baseline CCC  | Model 1 CCC  | Model 2 CCC |
| ------------- |-------------| -----|-----|
| Subject 1     | 0.01 | 0.59 | 0.35 |
| Subject 2     | 0.11 | 0.15 | 0.31 |
| Subject 3     | 0.04 | 0.50 | 0.45 |
| Subject 4     | 0.1 |  0.22 | 0.29 |
| Subject 5     | 0.11 | 0.28 | 0.24 |
| Subject 6     | 0.35 | 0.30 | 0.39 |
| Subject 7     | -0.01 | -0.16 |0.17 |
| Subject 8     | 0.05 | -0.01 |0.19 |
| Subject 9     | 0.05 | 0.11 |0.00 |
| Subject 10     | 0.10 | -0.02 |0.12 |
| Mean    | 0.091     |    0.19 | 0.25|


**Test results using five fold cross validation:**

| Subject       | Model 1 CCC  |
| ------------- |-------------|
| Subject 1     | 0.21 | 
| Subject 2     | 0.20 |
| Subject 3     | 0.27 |
| Subject 4     | 0.19 |
| Subject 5     | 0.21 |
| Subject 6     | 0.08 |
| Subject 7     | 0.10 |
| Subject 8     | 0.06 |
| Subject 9     | 0.09 |
| Subject 10     | 0.21 |
| Mean    | 0.16     |
