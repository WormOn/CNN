import theano
import theano.tensor as T
import numpy as np
from elements.util import BaseLayer

class OutputLayer(BaseLayer):
    '''
    Output layer for convolutional neural network. Support many different loss functions, which can be set in
    config.
    '''
    def __init__(self, rng, input, n_in, n_out, W=None, b=None, batch_size=32, loss='crossentropy', verbose=True):
        super(OutputLayer, self).__init__(rng, input, 0.0)
        self._verbose_print(verbose, n_in, n_out, loss, batch_size)

        if loss == 'bootstrapping':
            print('bootstrapping')
            self.negative_log_likelihood = self.loss_bootstrapping
        elif loss == 'crosstrapping':
            print('crosstrapping')
            self.negative_log_likelihood = self.loss_crosstrapping
        elif loss == 'bootstrapping_soft':
            print('bootstrapping_soft')
            self.negative_log_likelihood = self.loss_bootstrapping_soft
        elif loss == 'bootstrapping_confident':
            print('bootstrapping_confident')
            self.negative_log_likelihood = self.loss_confident_bootstrapping
        elif loss == 'bootstrapping_union':
            print('bootstrapping_union')
            self.negative_log_likelihood = self.loss_stochastic_union_bootstrapping
        else:
            print('crossentropy')
            self.negative_log_likelihood = self.loss_crossentropy



        W_bound = np.sqrt(6.0 / (n_in + n_out)) * 4
        self.set_weight(W, -W_bound, W_bound, (n_in, n_out))
        self.set_bias(b, n_out)

        self.output = T.nnet.sigmoid(T.dot(input, self.W) + self.b)
        self.output = T.clip(self.output, 1e-7, 1.0 - 1e-7)

        self.params = [self.W, self.b]
        self.input = input
        self.size = n_out * batch_size

    def loss_crossentropy(self, y, factor=1):
        return T.mean(T.nnet.binary_crossentropy(self.output, y))

    def loss_bootstrapping(self, y, factor=1):
        #Customized categorical cross entropy.
        #Based on the multibox impl. More tuned to paper.
        p = self.output
        hard = T.gt(p, 0.5)
        loss = (
            - T.sum( ((factor * y) + ((1.0- factor) * hard)) * T.log(p) ) -
            T.sum( ((factor * (1.0 - y)) + ((1.0- factor) * (1.0 - hard))) * T.log(1.0 - p) )
        )
        return loss/self.size


    def loss_bootstrapping_soft(self, y, factor=1):
        #Soft version of bootstrapping
        p = self.output
        loss = (
            - T.sum( ((factor * y) + ((1.0- factor) * p)) * T.log(p) ) -
            T.sum( ((factor * (1.0 - y)) + ((1.0- factor) * (1.0 - p))) * T.log(1.0 - p) )
        )
        return loss/self.size


    def loss_crosstrapping(self, y, factor=1):
        #Almost the same as bootstrapping, except mean used for overall result.
        #More closely follows crossentropy implementation.
        #When factor is 1, crossentropy equals this implementation. So performance
        #without decreasing factor should be the same!
        p = self.output
        hard = T.gt(p, 0.5)
        cross = - (
            (( factor * y * T.log(p) ) + ((1.0-factor) * hard * T.log(p) )) +
             (( factor* (1.0-y) * T.log(1.0-p) ) + ( (1.0-factor) * (1.0-hard) * T.log(1.0-p) ))
        )
        return T.mean(cross)

    def loss_confident_bootstrapping(self, y, factor=1):
        #Customized categorical cross entropy.
        #Based on the multibox impl. More tuned to paper. More strict
        p = self.output
        #Only confident predictions are included. Everything between 0.2 and 0.8 is disregarded. 60% of the range.
        hardUpper = T.gt(p, 0.8)
        hardLower = T.le(p, 0.2)
        loss = (
            - T.sum( ((factor * y) + ((1.0- factor) * hardUpper)) * T.log(p) ) -
            T.sum( ((factor * (1.0 - y)) + ((1.0- factor) * hardLower)) * T.log(1.0 - p) )
        )
        return loss/self.size

    def loss_stochastic_union_bootstrapping(self, y, factor=1):
        #Stochastic union bootstrapping. If factor over threshold, the union of confident prediction and label is returned
        random_nr = self.srng.uniform((1,))
        ny = T.switch(T.gt(random_nr[0], factor), T.or_(T.gt(self.output, 0.8), y), y)
        return T.mean(T.nnet.binary_crossentropy(self.output, ny))

    def errors(self, y):
        #Returns the mean squared error.
        # Prediction - label squared, for all cells in all batches and pixels.
        # Averaged by sum + divided by total number of elements. AKA - batch_size * dim * dim elements
       return T.mean(T.pow(self.output- y, 2))

    def _verbose_print(self, is_verbose, n_in, n_out, loss, batch_size):
        if is_verbose:
            print('Output layer with {} outputs'.format(n_out))
            print('---- Incoming connections: {}'.format(n_in))
            print('---- Sigmoidal units')
            print('---- Loss function: {}'.format(loss))
            print('---- Output dimension: {}'.format(n_out*batch_size))
            print('')
