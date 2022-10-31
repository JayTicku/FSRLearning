from dataclasses import dataclass
import numpy as np
from sklearn.ensemble import RandomForestClassifier

@dataclass
class State:
    '''
        State object
    '''
    number: list
    description: list
    v_value: float
    reward: float = 0
    nb_visited: int = 0

    def get_reward(self, X_train, y_train, X_test, y_test) -> float:
        '''
            Return the reward of a set of variable
        '''
        #Train classifier with state_t variable and state t+1 variables and compute the diff of the accuracy
        if self.reward == 0:
            clf = RandomForestClassifier(max_depth=2)
            clf.fit(X_train, y_train)
            accuracy: float = clf.score(X_test, y_test)
            self.reward = accuracy
            return accuracy
        else:
            return self.reward

    def select_action(self, feature_structure: dict, eps: float, aorf_histo: list):
        '''
            Return an action object

            This method enables to train only once a model and get the accuracy
        '''
        #Get possible neighbors of the current state
        neigh_state_depth: int = self.number[0] + 1
        if feature_structure.get(neigh_state_depth) is not None:
            state_neigh: list = [neigh for neigh in feature_structure[neigh_state_depth] if np.array_equal(self.description, neigh.description[:-1])]
        else:
            state_neigh: list = []

        #Random state selection
        select_random_element: int = None if not state_neigh else np.random.randint(len(state_neigh))
        next_state: State = None if not state_neigh else state_neigh[select_random_element]

        #Get current state object
        current_state: State = feature_structure[self.number[0]][self.number[1]]

        if self.nb_visited == 0 or next_state is None:
            #State never visited ==> we chose a random action
            possible_neigh: list = [np.append(self.description, i) for i in range(aorf_histo[0].shape[0]) if i not in self.description]

            select_random_element: int = np.random.randint(len(possible_neigh))

            next_state: State = State([self.number[0] + 1, 0], possible_neigh[select_random_element], 0, 0)

            #We update the number of visit
            self.nb_visited += 1

            return Action(current_state, next_state), next_state
        else:
            '''
            e_greedy_choice: bool = bool(np.random.binomial(1, eps))
            if e_greedy_choice:
                return Action(current_state, next_state), next_state
            else:'''
            #Get AOR of a variable and select the max AOR associated to a variable
            reward_by_state: list = [aorf_histo[1][rew.description[-1]] for rew in state_neigh if np.array_equal(self.description, rew.description[-1])]
            max_reward_index: int = np.argmax(reward_by_state)

            #We update the number of visit
            self.nb_visited += 1

            return Action(current_state, state_neigh[max_reward_index]), current_state.description + [state_neigh[max_reward_index]]                

            

    def update_v_value(self, alpha: float, gamma: float, v_value_next_state: float):
        '''
            Update the v_value of a state
        '''
        self.v_value += alpha * (self.reward + gamma * v_value_next_state - self.v_value)

    def is_final(self, nb_of_features: int) -> bool:
        '''
            Check if a state is a final state (with all the features in the state)

            Returns True if all the possible features are in the state
        '''
        if len(self.description) == nb_of_features:
            return True
        else:
            return False

    def is_equal(self, compared_state) -> bool:
        '''
            Compare if two State objects are equal

            Returns True if yes else returns False
        '''
        if np.array_equal(self.description, compared_state.description) and np.array_equal(self.number, compared_state.number):
            return True
        else:
            return False

@dataclass
class Action:
    '''
        Action Object
    '''
    state_t: State
    state_next: State              

    def get_aorf(self, aor_historic: list) -> float:
        '''
        Update the ARO of a feature

        Return the AOR table
        '''

        #Get historic
        chosen_feature: int = self.state_next.description[-1]
        aorf_nb_played_old: int = aor_historic[0][int(chosen_feature)]
        aorf_value_old: int = aor_historic[1][int(chosen_feature)]

        #Update the aor for the selection of f
        aor_historic[0][int(chosen_feature)] += 1  

        #Update the aor for the selection of f
        aor_historic[1][int(chosen_feature)] = ((aorf_nb_played_old - 1) * aorf_value_old + self.state_t.v_value) / (aorf_nb_played_old + 1)

        return aor_historic          

@dataclass
class FeatureSelectionProcessV2:
    '''
        Init aor list such that aor = [[np.zeros(nb_of_features)], [np.zeros(nb_of_features)]]

    '''
    nb_of_features: int
    eps: float
    alpha: float
    gamma: float

    #Memory of AORf [[nb f is selected], [AOR value]]
    aor: list

    #Init the state structure
    feature_structure: dict


    def pick_random_state(self) -> State:
        '''
            Select a random state in all the possible state space
            
            Return a state randomly picked
        '''
        random_start: int = np.random.randint(1, self.nb_of_features)
        random_end: int = np.random.randint(random_start, self.nb_of_features)
        chosen_state: list = np.random.default_rng(seed=42).permutation([var for var in range(self.nb_of_features)])[random_start:random_end]

        depth: int = len(chosen_state)

        #Check if the dict is empty
        if self.feature_structure.get(depth) is not None:
            return State([depth, len(self.feature_structure.get(depth))], chosen_state, 0, 0)
        else:
            return State([depth, 0], chosen_state, 0, 0)

    def start_from_empty_set(self) -> State:
        '''
            Start from the empty set (with no feature selected)
            
            Returns the empty initial state
        '''
        return State([0, 0], [], 0, 0)

    def add_to_historic(self, visited_state: State):
        '''
            Add to the feature structure historic function
        '''
        depth = visited_state.number[0]
        if depth in self.feature_structure:
            is_in_table: bool = [visited_state.is_equal(state) for state in self.feature_structure[depth]]
            get_index_where_true: int = [is_in_table.index(i) for i in is_in_table if i] if np.any(is_in_table) else None
            if get_index_where_true is not None:
                self.feature_structure[depth][get_index_where_true[0]] = visited_state
            else:
                self.feature_structure[depth].append(visited_state)
        else:
            self.feature_structure[depth] = [visited_state]

    def get_final_aor_sorted(self) -> list:
        '''
            Returns the aor table sorted by ascending

            Index of the feature
            Number of time the feature has been played
            Value of the feature
            Best feature (from the lowest to the biggest)
        '''

        index: list = [i for i in range(self.nb_of_features)]
        nb_played: list = self.aor[0]
        values: list = self.aor[1]

        index, values = zip(*sorted(zip(index, values)))

        return [index, nb_played, values, np.argsort(self.aor[1])]




    
    

    

    