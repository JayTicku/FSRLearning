from dataclasses import dataclass
from operator import index

#Maths and others
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import itertools

#Other class
from .feature_selection_RL_V2 import *

#ML Sklearn library
from sklearn.feature_selection import RFE
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split


@dataclass
class Feature_Selector_RL:
    '''
        This is the class used to create a feature selector with the RL method

        fit enable to get the results structured as follows:
            [
                Feature index : list,
                Number of times a feature has been played: list
                AOR value per feature: list,
                Sorted list of feature from the less to the most important for the model: list
            ]
    '''

    feature_number: int
    nb_explored: list
    nb_not_explored: list
    feature_structure: dict
    aor: list = None
    eps: float = .1
    alpha: float = .5
    gamma: float = .99
    nb_iter: int = 100
    explored: int = 0
    not_explored: int = 0


    def fit_transform(self, X, y) -> list:

        #We init the process
        print('---------- AOR init ----------')
        self.aor = [np.zeros(self.feature_number), np.zeros(self.feature_number)]

        print('---------- Process init ----------')
        feature_selection_process = FeatureSelectionProcessV2(self.feature_number, self.eps, self.alpha, self.gamma, self.aor, self.feature_structure)

        print('---------- Data Processing ----------')
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)

        print('---------- The process has been successfully init ----------')

        print('---------- Training ----------')

        for it in tqdm(range(self.nb_iter)):

            #print(f'Current state selection {it} ---------')
            current_state = feature_selection_process.start_from_empty_set()
            
            not_worsen_value: bool = True
            previous_state_v_value, nb_iter_after_actu = 0, 0

            while current_state.number[0] <= 13 or not_worsen_value:

                #We get the reward of the state
                if current_state.reward == 0:
                    current_state.get_reward(X_train, y_train, X_test, y_test)

                #We chose the next state
                return_next_action_state = current_state.select_action(feature_selection_process.feature_structure, feature_selection_process.eps, feature_selection_process.aor)
                next_state, next_action = return_next_action_state[1], return_next_action_state[0]

                previous_state_v_value = next_state.v_value

                if current_state.v_value == 0:
                    self.explored += 1
                else:
                    #We add the state as an already explored state
                    self.not_explored += 1

                if len(next_action.state_next.description) >= 14:
                    break

                #We get the reward of the state
                if next_state.reward == 0:
                    next_state.get_reward(X_train, y_train, X_test, y_test)

                #We update the v_value of the state
                current_state.update_v_value(feature_selection_process.alpha, feature_selection_process.gamma, next_state)

                #We update the aor table
                feature_selection_process.aor = next_action.get_aorf(feature_selection_process.aor)

                #Add the state to the research tree
                feature_selection_process.add_to_historic(current_state)

                if current_state.v_value < previous_state_v_value and nb_iter_after_actu == 1:
                    print('Stop because worsen')
                    not_worsen_value = False

                current_state = next_state
                nb_iter_after_actu += 1
                
            self.nb_explored.append(self.explored)
            self.nb_not_explored.append(self.not_explored)

        results = feature_selection_process.get_final_aor_sorted()

        
        return results

    def get_plot_ratio_exploration(self):

        plt.plot([i for i in range(len(self.nb_not_explored))], self.nb_not_explored, label='Not Explored State')
        plt.plot([i for i in range(len(self.nb_explored))], self.nb_explored, label='Explored State')
        plt.xlabel('Number of iterations')
        plt.ylabel('Number of states')
        plt.legend(loc="upper left")

        plt.show()

    def compare_with_benchmark(self, X, y, results) -> list:
        is_better_list: list = []
        avg_benchmark_acccuracy: list = []
        avg_rl_acccuracy: list = []

        print('---------- Data Processing ----------')
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)

        print('---------- Score ----------')
        for i in range(1, self.feature_number):
            #From RL
            clf = RandomForestClassifier(max_depth=4)
            clf.fit(X_train[results[-1][i:]], y_train)
            accuracy: float = clf.score(X_test[results[-1][i:]], y_test)

            #Benchmark
            estimator = RandomForestClassifier(max_depth=4)
            selector = RFE(estimator, n_features_to_select=len(results[-1]) - i, step=1)
            selector = selector.fit(X_train, y_train)
            sele_acc = selector.score(X_test, y_test)

            if accuracy >= sele_acc:
                is_better_list.append(1)
            else:
                is_better_list.append(0)
            
            avg_benchmark_acccuracy.append(sele_acc)
            avg_rl_acccuracy.append(accuracy)

            print(f'Set of variables : Benchmark : {X_train.columns[selector.support_].tolist()} and RL : {results[-1][i:]}')
            print(f'Benchmark accuracy : {sele_acc}, RL accuracy : {accuracy} with {len(results[-1]) - i} variables {is_better_list}')
        
        print(f'Average benchmark accuracy : {np.mean(avg_benchmark_acccuracy)}, rl accuracy : {np.mean(avg_rl_acccuracy)}')

        index_variable: list = [i for i in range(len(avg_benchmark_acccuracy))]

        avg_benchmark_acccuracy.reverse()
        avg_rl_acccuracy.reverse()

        plt.plot(index_variable, avg_benchmark_acccuracy, label='Benchmark acccuracy')
        plt.plot(index_variable, avg_rl_acccuracy, label='RL accuracy')
        plt.xlabel('Number of variables')
        plt.ylabel('Accuracy')
        plt.legend(loc="lower right")

        plt.show()

        return is_better_list

    def get_best_state(self):
        '''
            Returns the optimal state
        '''

        optimal_state: State = State([0, 0], [], 0)

        #Dictionary browsing by key
        for key in self.feature_structure.keys():
            if key == 0:
                pass
            else:
                for value in self.feature_structure[key]:
                    if value.v_value > optimal_state.v_value:
                        optimal_state = value

        return optimal_state