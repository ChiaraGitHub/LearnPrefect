import os
import pickle

output_folder = 'local_results'
for file_name in os.listdir(output_folder):
    f = open(os.path.join(output_folder, file_name), 'rb')
    content = f.read()
    print(pickle.loads(content))
