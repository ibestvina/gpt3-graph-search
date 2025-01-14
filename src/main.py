import random
import time

from gpt3_api import execute
from random import shuffle, choice
from collections import deque
import re
import json
import uuid
import openai


def format_node_name(node):
    return node  # no op for now, but we might want to try named nodes


def format_solution(solution):
    if not solution or solution.lower().startswith(no_path_reason):
        return no_path_reason
    return ','.join(str(n) for n in solution)


def other(edge, fr):
    if edge[0] == fr:
        return edge[1]
    else:
        return edge[0]


no_path_reason = 'there is no path'


class RandomGraph:
    def __init__(self, node_count, edge_count, force_solution=False, force_path_len=None):
        self.force_solution = force_solution
        self.force_path_len = force_path_len
        assert (node_count < 100)
        assert (edge_count < node_count * (node_count - 1) / 2)
        self.generate(node_count, edge_count)
        self.raw_gpt_answer = self.gpt_solve()['choices'][0]['text']
        self.gpt3_solution = self.extract_gpt_answer(self.raw_gpt_answer)
        self.guid = uuid.uuid4()

    def generate(self, node_count, edge_count, tries_left=10):
        edges = [(a, b) for a in range(1, node_count + 1) for b in range(1, node_count + 1) if a < b]
        shuffle(edges)

        self.nodes = list(range(1, node_count + 1))
        self.edges = edges[:edge_count]
        self.neighbors_of_node = {
            node: [other(edge, node) for edge in self.edges if node in edge] for node in self.nodes
        }
        self.from_location = choice(self.nodes)
        self.to_location = choice([node for node in self.nodes if node != self.from_location])
        self.solution = self.solve()

        if tries_left > 0:
            if not self.solution and self.force_solution:
                self.generate(node_count, edge_count, tries_left - 1)  # try again
            if self.force_path_len and (not self.solution or len(self.solution) != self.force_path_len):
                self.generate(node_count, edge_count, tries_left - 1)

    def extract_gpt_answer(self, answer):
        stripped = answer.strip()
        if stripped.lower().startswith(no_path_reason):
            return None
        nodes = [int(s[2:]) for s in re.findall(r'-[ ]\d+', answer)]
        last_node = int(re.findall(r'\d+', stripped)[-1])
        nodes.append(last_node)
        return nodes

    def gpt_solve(self):
        return execute(
            self.prompt(), 
            temperature=0,
            max_tokens=1256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=["```"]
        )

    def solve(self):
        q = deque([(self.from_location, [])])
        seen = set()
        while len(q):
            (top, path) = q.popleft()
            if top in seen:
                continue
            seen.add(top)
            if top == self.to_location:
                return [format_node_name(n) for n in path + [top]]
            for n in self.neighbors_of_node[top]:
                q.append((n, path + [top]))

        return None

    def grade_gpt_answer(self):
        if not self.gpt3_solution:
            if not self.solution:
                return (True, "There was no solution and GPT-3 correctly figured it out!")
            return (False, "There was a solution but GPT-3 thought there wasn't one")

        if not len(self.gpt3_solution):
            return (False, "GPT-3 returned an answer we couldn't parse.")

        gpt_solution = self.gpt3_solution[:]
        last = None
        is_correct_length = self.solution and len(gpt_solution) == len(self.solution)
        bad_edges = []

        # Iterate through the solution, looking for bad edges and also looking for embedded solutions.

        partial_solution = None
        found_embedded_solution = None
        for node in gpt_solution:
            is_edge_ok = True
            if last and node not in self.neighbors_of_node[last]:
                bad_edges.append((last, node))
                partial_solution = None
                is_edge_ok = False

            # Searching for a solution inside the string
            if node == self.from_location:
                partial_solution = [node]
            elif node == self.to_location and partial_solution and is_edge_ok:
                partial_solution.append(node)
                found_embedded_solution = partial_solution
                partial_solution = None
            elif partial_solution and is_edge_ok:
                partial_solution.append(node)

            last = node

        if not self.solution:
            return (False,
                    f"There was no solution but GPT-3 found one. Their solution was {len(gpt_solution)} nodes and included the following {len(bad_edges)} incorrect edges: {'|'.join((str(be) for be in bad_edges))}")
        if gpt_solution[0] != self.from_location:
            return (
                False,
                f"GPT-3's solution started with the wrong node: {gpt_solution[0]} instead of {self.from_location}")

        embedded_solution_msg = f"There was a correct solution embedded inside the path, though: {','.join(str(n) for n in found_embedded_solution)}" if found_embedded_solution else ""

        if len(bad_edges):
            return (False,
                    f"GPT-3 tried to used some edges that don't exist. They are: {'|'.join((str(be) for be in bad_edges))}. {embedded_solution_msg}")
        if last != self.to_location:
            return (False,
                    f"GPT-3 ended up in the wrong place! ({last} instead of {self.to_location}). {embedded_solution_msg}")

        if is_correct_length:
            return (True, f"GPT-3 got the optimal solution of {len(gpt_solution)} steps!")

        return (True,
                f"GPT-3 found a solution -- though it took {len(gpt_solution)} steps instead of the optimal {len(self.solution)} steps")

    def prompt(self):
        newline = '\n'
        problem = newline.join(f'{format_node_name(edge[0])} is connected to {format_node_name(edge[1])}' for edge in self.edges)
        return f'''
Problem:
```
1 is connected to 2.
1 is connected to 4.
```
Question: 
```
What is the shortest path from 4 to 1?
```
Answer:
```
- 4 to 1
```


Problem:
```
3 is connected to 2.
4 is connected to 3.
```
Question:
```
What is the shortest path from 2 to 4?
```
Answer:
```
- 2 to 3
- 3 to 4
```

 
Problem:
```
3 is connected to 2.
4 is connected to 3.
5 is connected to 6.
```
Question:
```
What is the shortest path from 2 to 6?
```
Answer:
```
There is no path from 2 to 6
```

 
 
Problem:
```
{problem}
```
Question: 
```
What is the shortest path from {format_node_name(self.from_location)} to {format_node_name(self.to_location)}?
```
Answer:
```
'''

    def as_record(self):
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "solution": self.solution,
            "prompt": self.prompt(),
            "gpt3_raw": self.raw_gpt_answer,
            "grade": self.grade_gpt_answer(),
            "uuid": str(self.guid)
        }


def generate_many_graphs():
    data = []
    file_name = f'data-{uuid.uuid4()}.json'

    for _ in range(1000):
        force_solution = random.random() < 0.5  # Half the time, force the graph to be solveable
        force_path_len = None if not force_solution else random.randint(2, 7)
        node_count = random.randint(3, 14) if not force_path_len else force_path_len * 2
        edge_count = min(25, random.randint(1, int(node_count * (node_count - 1) / 2) - 1))

        try:
            graph = RandomGraph(node_count, edge_count, force_solution, force_path_len)
            grade = graph.grade_gpt_answer()
        except openai.error.RateLimitError:
            print('sleeping...')
            time.sleep(10)
            continue
        if grade[0]:
            print("YES", node_count, edge_count, len(graph.solution) if graph.solution else 0, graph.solution,
                  graph.gpt3_solution, grade[1], graph.guid, force_path_len)
        else:
            print("NO", node_count, edge_count, len(graph.solution) if graph.solution else 0, graph.solution,
                  graph.gpt3_solution, grade[1], graph.guid, force_path_len)
        data.append(graph.as_record())

        # Save the result incrementally in case of crashes
        with open(file_name, 'w') as handle:
            json.dump(data, handle)
        
        time.sleep(5)
    print("Data is in " + file_name)


if __name__ == '__main__':
    generate_many_graphs()
