import sys, os

sys.path.append(os.path.abspath("./"))

import util

'''
This tool creates a loss figure containing, training, test and validation error. It averages experiment runs before
constructing a figure.
'''

path = '/home/olav/Documents/Results/E7_road_detection_performance'
folder = 'Network M1'
lc_key_x = 'epoch'

print("Creating averaged loss figures")
paths = os.listdir(os.path.join(path, folder))

data = []

for data_path in paths:
    json_data = util.open_json_result(os.path.join(path, folder,data_path))
    if type(json_data) is list:
            d = json_data[0]
    else:
        d = json_data
    data.append(d)


loss_avg = util.average(data, 'events', lc_key_x)
series = [
    {"name": "Training loss", "data": loss_avg, "y_key":  "training_loss"},
    #{"name": "Validation loss", "data": loss_avg, "y_key":  "validation_loss"},
    {"name": "Test loss", "data": loss_avg, "y_key":  "test_loss"}
]
util.display_loss_curve_plot(series)