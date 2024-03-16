import numpy as np
import os
import time
import pickle

from abc import ABC, abstractmethod
from sklearn.mixture import GaussianMixture

class Rehearsal(ABC):
    """
    Abstract class for managing rehearsal data.
    """
    def __init__(self, data_set, num_samples_per_class, path='saves'):
        self.rehearsal = {}
        self.num_samples_per_class = num_samples_per_class
        self.task_creation_time = {}
        self.task_creation_time_wall = {}
        self.class_creation_time = {}
        self.save_path = os.path.join(path, data_set, 'rehearsal_data.pkl')
    
    @property
    def new_task_id(self):
        return len(self.task_creation_time)

    def add_task(self, task_data):
        task_start = time.process_time()
        task_start_wall = time.time()

        features, labels = task_data['x'], task_data['y']
        classes = np.unique(labels)
        for class_id in classes:
            class_start = time.process_time()

            class_features = features[labels == class_id]
            self.add_class(class_id, class_features)

            class_end = time.process_time()
            self.class_creation_time[class_id] = class_end - class_start

        task_end = time.process_time()
        task_end_wall = time.time()
        self.task_creation_time[self.new_task_id] = task_end - task_start
        self.task_creation_time_wall[self.new_task_id] = task_end_wall - task_start_wall

    @abstractmethod
    def add_class(self, class_id, class_features):
        """
        Abstract method to process a new class's data.
        """
        pass

    @abstractmethod
    def generate_rehearsal_data(self):
        """
        Abstract method to generate pseudo-rehearsal data.
        """
        pass

    def save(self):
        """
        Saves data to the specified save path using numpy's npz format.
        """
        with open(self.save_path, 'wb') as file:
            pickle.dump(self.rehearsal, file)

    def load(self):
        """
        Loads data from the specified save path into the object.
        """
        with open(self.save_path, 'rb') as file:
            self.rehearsal = pickle.load(file)



class GaussianDistribution(Rehearsal):
    """
    Manages rehearsal data through a Gaussian Distribution.
    """
    def __init__(self, data_set, path='saves', **kwargs):
        super().__init__(data_set, path)
        self.class_means = []
        self.class_covariances = []

    def add_class(self, class_id, class_features):
        mean = np.mean(class_features, axis=0)
        cov = np.cov(class_features, rowvar=False)
        self.rehearsal[class_id] = (mean, cov)

    def generate_rehearsal_data(self):
        rehearsal_features = []
        rehearsal_labels = []

        for class_id, (mean, cov) in self.rehearsal.items():
            samples = np.random.multivariate_normal(mean, cov, self.num_samples_per_class)
            rehearsal_features.append(samples)
            rehearsal_labels.append(np.full(self.num_samples_per_class, class_id))

        return np.concatenate(rehearsal_features, dtype=np.float32), np.concatenate(rehearsal_labels, dtype=np.float32)


class GaussianMixtureModel(Rehearsal):
    """
    Manages rehearsal data through Gaussian Mixture Models.
    """
    def __init__(self, data_set, num_samples_per_class=10, components_range=[2, 3, 4], seed=None, path='saves', **kwargs):
        super().__init__(data_set, num_samples_per_class, path)
        self.components_range = components_range
        self.seed = seed
    
    def add_class(self, class_id, class_features):
        best_gmm, best_score = None, np.inf
        for n_components in self.components_range:
            gmm = GaussianMixture(n_components=n_components, random_state=self.seed).fit(class_features)
            bic = gmm.bic(class_features)
            if bic < best_score:
                best_gmm, best_score = gmm, bic
        self.rehearsal[class_id] = best_gmm

    def generate_rehearsal_data(self):
        rehearsal_data = []
        rehearsal_labels = []
        for class_id, gmm in self.rehearsal.items():
            samples, _ = gmm.sample(self.num_samples_per_class)
            rehearsal_data.append(samples)
            rehearsal_labels.append(np.full(self.num_samples_per_class, class_id))

        return np.concatenate(rehearsal_data, dtype=np.float32), np.concatenate(rehearsal_labels, dtype=np.float32)