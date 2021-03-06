import argparse
import swifter
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

from utils import configuration
from utils.configuration import *
from utils.preprocessor import *

changeToColabPath(configuration.colab)
createDirectory()

def preprocess_raw_data(from_file, lang, min_inp_len=64, max_inp_len=256, min_tar_len=16, max_tar_len=256, 
                        size=None, split=False, plot=False, random_state=24601):
    name = from_file[from_file.rfind('/')+1:]
    print(f"\nStart process raw data - {name}...\n")
    
    # load and parse
    if 'news2016zh' in from_file:
        data_head = {k:v for k, v in enumerate(['news_id', 'keywords', 'desc', 'title', 'source', 'time', 'content'])}
        data = pd.read_csv(from_file, header=None).rename(columns=data_head)[['title', 'content']]
        data = data.assign(**{c:data[c].str.replace(f'"{c}": "', '').str[:-1] for c in data.columns})
    elif 'lcsts_data' in from_file:
        data = pd.read_json(configuration.DIR_DATA+'/zh/lcsts_data.json')
        # remove hashtag & quotation marks in label column
        data = data.assign(title=data.title.str.replace('#|“|”', ''))
    
    # specify the length range for datasets
    print(' Before clean, data size is:, ', len(data))
    data = data.assign(length_inp=data.content.apply(len))
    data = data[(min_inp_len<=data.length_inp)&(data.length_inp<=max_inp_len)]
    data = data.assign(length_tar=data.title.apply(len))
    data = data[(min_tar_len<=data.length_tar)&(data.length_tar<=max_tar_len)]
    print(' After clean, data size is:, ', len(data))

    # sample part of data
    if size:
        size = min(size, len(data))
        data = data.sample(n=size, replace=False, random_state=random_state)

    # show size & plot distribution
    print("  Data Size: ", data.shape[0])
    for col_name, col in zip(['source', 'target'], ['length_inp', 'length_tar']):
        plt.hist(data[col], bins=100)
        if plot:
            print(f"  Plot length distribution of {col_name}")
            plt.show()
        else:
            plt.savefig(f'../reports/figures/data-{name}-{col_name}.jpg')
        data = data.drop(col, axis=1)

    # preprocess texts & labels
    print("  Preprocess & Transfer from Simplified Chinese to Tranditional Chinese...")
    data = data.swifter.applymap(lambda text:preprocessors[lang](cc.convert(text), py_function=True)[0])
    data = data.dropna().reset_index(drop=True)
    
    # split dataset & output
    data = data.rename(columns={'title':'target', 'content':'source'})
    if split:
        data_train, data_valid = train_test_split(data, test_size=split, random_state=random_state)
        return data_train, data_valid
    else:
        return data

    
config = configparser.ConfigParser()
config.read('../config/model.cfg')

### read configurations

seed = config['basic'].getint('seed')

lang = config['data']['lang']
test_file = config['data']['test_file']
train_file = config['data']['train_file']
  
min_inp_len = config['data'].getint('min_inp_len')    
max_inp_len = config['data'].getint('max_inp_len')
min_tar_len = config['data'].getint('min_tar_len')    
max_tar_len = config['data'].getint('max_tar_len')

if __name__ == '__main__':

    # setup size
    train_size = config['data'].getint('train_size')
    test_size = config['data'].getint('test_size')  

    # setup path
    train_from_path = os.path.join(configuration.DIR_DATA, lang, train_file)
    test_from_path = os.path.join(configuration.DIR_DATA, lang, test_file)
    
    to_path = os.path.join(configuration.DIR_INTERMIN, lang)
    if not os.path.isdir(to_path):
        os.makedirs(to_path, exist_ok=True)
    train_to_path = os.path.join(to_path, 'train.zip')
    valid_to_path = os.path.join(to_path, 'valid.zip')
    test_to_path = os.path.join(to_path, 'test.zip')

    # preprocess 
    if test_file:
        test = preprocess_raw_data(test_from_path, lang, min_inp_len, max_inp_len, min_tar_len, max_tar_len,
                                   size=test_size, random_state=seed)
        test_size = len(test)
    else:
        test = None
        test_size *= 2

    train, valid = preprocess_raw_data(train_from_path, lang, min_inp_len, max_inp_len, min_tar_len, max_tar_len,
                                       size=train_size, split=test_size, random_state=seed)
    if not bool(test):
        valid, test = train_test_split(valid, test_size=0.5, random_state=seed)
    
    # save to intermin directory
    train.to_csv(train_to_path, index=None)
    valid.to_csv(valid_to_path, index=None)
    test.to_csv(test_to_path, index=None)
