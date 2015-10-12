from evaluator import Evaluator
from model import Model
from data import MnistDataset, AerialDataset
from storage.store import ParamStorage
import os
from config import model_params, optimization_params, dataset_params, filename_params, visual_params, number_of_epochs, verbose
def run_cnn(model_params, optimization_params, dataset, dataset_params, filename_params, visual_params, epochs, verbose=False):
    print(filename_params)
    if not os.path.exists(filename_params.results):
        os.makedirs(filename_params.results)

    d = AerialDataset()
    d.load(dataset, dataset_params) #Input stage
    m = Model(model_params, verbose=True) #Create network stage
    e = Evaluator(m, d)
    e.evaluate(optimization_params, epochs=epochs,  verbose=verbose)

    #Stores the model params. Model can later be restored.
    p = ParamStorage(path=filename_params.network_save_name)
    p.store_params(m.params)



run_cnn(
    model_params            = model_params,
    optimization_params     = optimization_params,
    dataset                 = 'C:\\Users\\olav\\Pictures\\Mass_roads',
    dataset_params          = dataset_params,
    filename_params         = filename_params,
    visual_params           = visual_params,
    epochs                  = number_of_epochs,
    verbose                 = verbose,
)