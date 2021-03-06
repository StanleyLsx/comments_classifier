# -*- coding: utf-8 -*-
# @Time : 2020/10/20 11:03 下午
# @Author : lishouxian
# @Email : gzlishouxian@gmail.com
# @File : predict.py
# @Software: PyCharm
import tensorflow as tf
import time
from config import classifier_config


class Predictor:
    def __init__(self, data_manager, logger):
        hidden_dim = classifier_config['hidden_dim']
        classifier = classifier_config['classifier']
        self.dataManager = data_manager
        self.seq_length = data_manager.max_sequence_length
        num_classes = data_manager.max_label_number
        self.embedding_dim = data_manager.embedding_dim
        vocab_size = data_manager.vocab_size

        self.logger = logger
        # 卷集核的个数
        num_filters = classifier_config['num_filters']
        self.checkpoints_dir = classifier_config['checkpoints_dir']
        self.embedding_method = classifier_config['embedding_method']
        if self.embedding_method == 'Bert':
            from transformers import TFBertModel
            self.bert_model = TFBertModel.from_pretrained('bert-base-multilingual-cased')
        logger.info('loading model parameter')
        if classifier == 'textcnn':
            from engines.models.textcnn import TextCNN
            self.model = TextCNN(self.seq_length, num_filters, num_classes, self.embedding_dim, vocab_size)
        elif classifier == 'textrcnn':
            from engines.models.textrcnn import TextRCNN
            self.model = TextRCNN(self.seq_length, num_classes, hidden_dim, self.embedding_dim, vocab_size)
        elif classifier == 'textrnn':
            from engines.models.textrnn import TextRNN
            self.model = TextRNN(self.seq_length, num_classes, hidden_dim, self.embedding_dim, vocab_size)
        else:
            raise Exception('config model is not exist')
        # 实例化Checkpoint，设置恢复对象为新建立的模型
        checkpoint = tf.train.Checkpoint(model=self.model)
        # 从文件恢复模型参数
        checkpoint.restore(tf.train.latest_checkpoint(self.checkpoints_dir))
        logger.info('loading model successfully')

    def predict_one(self, sentence):
        """
        对输入的句子分类预测
        :param sentence:
        :return:
        """
        reverse_classes = {class_id: class_name for class_name, class_id in self.dataManager.class_id.items()}
        start_time = time.time()
        vector = self.dataManager.prepare_single_sentence(sentence)
        if self.embedding_method == 'Bert':
            vector = self.bert_model(vector)[0]
        logits = self.model(inputs=vector)
        prediction = tf.argmax(logits, axis=-1)
        prediction = prediction.numpy()[0]
        self.logger.info('predict time consumption: %.3f(ms)' % ((time.time() - start_time)*1000))
        return reverse_classes[prediction]

    def save_model(self):
        # 保存pb格式的模型到本地
        if self.embedding_method == 'Bert':
            tf.saved_model.save(self.model, self.checkpoints_dir,
                                signatures=self.model.call.get_concrete_function(
                                    tf.TensorSpec([None, self.seq_length, 768], tf.float32, name='inputs')))
        elif self.embedding_method == 'word2vec':
            tf.saved_model.save(self.model, self.checkpoints_dir,
                                signatures=self.model.call.get_concrete_function(
                                    tf.TensorSpec(
                                        [None, self.seq_length, self.embedding_dim], tf.float32, name='inputs')))
        else:
            tf.saved_model.save(self.model, self.checkpoints_dir,
                                signatures=self.model.call.get_concrete_function(
                                    tf.TensorSpec([None, self.seq_length], tf.float32, name='inputs')))
        self.logger.info('The model has been saved')
