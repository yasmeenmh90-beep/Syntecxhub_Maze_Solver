import random
import unittest
from collections import deque
from maze_solver import astar

class SolverTests(unittest.TestCase):
    def test_shortest_paths_against_bfs(self):
        rng = random.Random(42)
        for _ in range(100):
            grid = [[int(rng.random()<0.3) for _ in range(8)] for _ in range(8)]
            grid[0][0] = grid[7][7] = 0
            queue, seen, distance = deque([((0,0),0)]), {(0,0)}, None
            while queue:
                p,d = queue.popleft()
                if p==(7,7):
                    distance=d
                    break
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    q=(p[0]+dr,p[1]+dc)
                    if 0<=q[0]<8 and 0<=q[1]<8 and not grid[q[0]][q[1]] and q not in seen:
                        seen.add(q)
                        queue.append((q,d+1))
            path,_ = astar(grid,(0,0),(7,7))
            self.assertEqual(None if path is None else len(path)-1,distance)
            if path:
                self.assertEqual(path[0],(0,0))
                self.assertEqual(path[-1],(7,7))
                for a,b in zip(path,path[1:]):
                    self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]),1)
                    self.assertEqual(grid[b[0]][b[1]],0)

    def test_unreachable(self):
        self.assertIsNone(astar([[0,1,0]],(0,0),(0,2))[0])

    def test_same_start_goal(self):
        self.assertEqual(astar([[0]],(0,0),(0,0))[0],[(0,0)])

    def test_invalid_inputs(self):
        for grid,start,goal in [([], (0,0),(0,0)), ([[0],[0,0]],(0,0),(0,0)), ([[1]],(0,0),(0,0)), ([[0]],(-1,0),(0,0)), ([[2]],(0,0),(0,0))]:
            with self.assertRaises(ValueError):
                astar(grid,start,goal)

if __name__=='__main__':
    unittest.main()
