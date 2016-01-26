

import numpy as np
import theano
import theano.tensor as T
import timeit
from util import debug_input_data, print_section, print_test, print_valid
import random
from sdg import Backpropagation
import gui.server
from config import visual_params
from wrapper import create_theano_func, create_profiler_func

class Evaluator(object):


    def __init__(self, model, dataset, params):
        self.data = dataset
        self.model = model
        self.params = params
        if(visual_params.gui_enabled):
            gui.server.start_new_job()


    def run(self, epochs=10, verbose=False):
        batch_size = self.params.batch_size
        self._build(batch_size)
        self._train(batch_size, epochs)


    def _build(self, batch_size):
        print_section('Building model')

        index = T.lscalar()  # index to a [mini]batch
        x = T.matrix('x')   # the data is presented as rasterized images
        y = T.imatrix('y')
        learning_rate = T.scalar('learning_rate', dtype=theano.config.floatX)

        self.model.build(x, batch_size)
        errors = self.model.get_output_layer().errors(y)

        self.test_model = create_theano_func('test', self.data, x, y, [index], errors, batch_size)
        self.validate_model = create_theano_func('validation', self.data, x, y, [index], errors, batch_size)

        cost = self.model.get_cost(y) + (self.params.l2_reg * self.model.getL2())
        opt = Backpropagation.create(self.model.params)
        grads = T.grad(cost, self.model.params)
        updates = opt.updates(self.model.params, grads, learning_rate, self.params.momentum)

        self.train_model = create_theano_func('train', self.data, x, y, [index, learning_rate], cost, batch_size, updates=updates)

        self.tester = create_profiler_func(self.data, x, y, [index], self.model.get_output_layer() ,cost, batch_size)


    def _debug(self, batch_size, minibatch_index):
        number_of_tests = 1
        #output, y, cost, errs = self.tester(minibatch_index)
        for test in range(number_of_tests):
            v = random.randint(0,batch_size-1)
            output, y, cost, errs = self.tester(minibatch_index)
            print(errs)
            print(cost)
            print(v)
            img = self.data.set['train'][0][(minibatch_index*batch_size) + v].eval()
            debug_input_data(img, output[v], 64, 16)
            debug_input_data(img, y[v], 64, 16)


    def _evaluate(self):
        #TODO: smart way to test and validation stuff from while loop in here?
        pass


    def _train(self, batch_size, max_epochs):
        print_section('Training model')
        #TODO: Inner forloop for changing content of training set
        n_train_batches = self.data.get_total_number_of_batches(batch_size)
        n_valid_batches = self._get_number_of_batches('validation', batch_size)
        n_test_batches = self._get_number_of_batches('test', batch_size)

        patience = self.params.initial_patience # look as this many examples regardless
        patience_increase = self.params.patience_increase  # wait this much longer when a new best is found
        improvement_threshold = self.params.improvement_threshold # a relative improvement of this much is considered significant

        # go through this many minibatch before checking the network on the validation set
        validation_frequency = min(n_train_batches, patience / 2)
        learning_rate = self.params.initial_learning_rate/float(batch_size)
        print('Effective learning rate {}'.format(learning_rate))
        learning_adjustment = 30
        best_validation_loss = np.inf
        best_iter = 0
        test_score = 0.
        start_time = timeit.default_timer()

        nr_chunks = self.data.get_chunk_number()
        epoch = 0
        done_looping = False
        iter = 0

        while (epoch < max_epochs) and (not done_looping):
            epoch = epoch + 1
            if(epoch % learning_adjustment == 0):
                    learning_rate *= 0.95
                    print('---- New learning rate {}'.format(learning_rate))

            for chunk_index in range(nr_chunks):
                #print(nr_chunks)

                #Switch content on GPU
                self.data.switch_active_training_set( chunk_index )
                nr_elements = self.data.get_elements( chunk_index )
                chunk_batches = nr_elements / batch_size
                #print(self.data.set['train'][0].eval())
                #Each chunk contains a certain number of batches.
                for minibatch_index in range(chunk_batches):
                    cost_ij = self.train_model(minibatch_index, learning_rate)
                    if iter % 100 == 0:
                        print('---- Training @ iter = {}'.format(iter))

                    if epoch > 4 and (iter + 1) % (validation_frequency * 10) == 0:
                        pass
                        #self._debug(batch_size, minibatch_index )

                    if(np.isnan(cost_ij)):
                        print('cost IS NAN')

                    #TODO: move to function - this is not run that often, and is kind of a unit.
                    if (iter + 1) % validation_frequency == 0:
                        if visual_params.gui_enabled:
                            gui.server.get_stop_status()

                        validation_losses = [self.validate_model(i) for i
                                             in range(n_valid_batches)]
                        this_validation_loss = np.mean(validation_losses)
                        #TODO: n_train_batches not correct
                        print_valid(epoch, minibatch_index + 1, n_train_batches,  this_validation_loss/batch_size)

                        # if we got the best validation score until now
                        if this_validation_loss < best_validation_loss:

                            #improve patience if loss improvement is good enough
                            if this_validation_loss < best_validation_loss * improvement_threshold:
                                patience = max(patience, iter * patience_increase)

                            # save best validation score and iteration number
                            best_validation_loss = this_validation_loss
                            best_iter = iter

                            # test it on the test set
                            test_losses = [
                                self.test_model(i)
                                for i in range(n_test_batches)
                            ]
                            print(test_losses)
                            test_score = np.mean(test_losses)
                            print_test(epoch, minibatch_index + 1, n_train_batches,  test_score/batch_size)

                            if visual_params.gui_enabled:
                                #TODO: Only test when validation is better, so move this out of inner scope.
                                gui.server.append_job_update(epoch, cost_ij, this_validation_loss/batch_size, test_score/batch_size)

                    if patience <= iter:
                        done_looping = True
                        break
                    if visual_params.gui_enabled and gui.server.stop:
                        done_looping = True

                    iter += 1 #Increment interation after each batch has been processed.

        end_time = timeit.default_timer()
        print('Optimization complete.')
        print('Best validation score of %f %% obtained at iteration %i, '
              'with test performance %f %%' %
              (best_validation_loss * 100., best_iter + 1, test_score * 100.))
        print('The code ran for %.2fm' % ((end_time - start_time) / 60.))



    def _get_number_of_batches(self, set_name, batch_size):
        set_x, set_y = self.data.set[set_name]
        nr_of_batches = set_x.get_value(borrow=True).shape[0]
        nr_of_batches /= batch_size
        return int(nr_of_batches)

