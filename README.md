# *In development
Chess game with AI opponent made in Python.  
GUI made with Pygame. 

Can choose between Player or AI for both side selections making it possible to play:  
Player vs AI, Player vs Player or AI vs AI.  
AI can be set to three different difficulty levels.

The move generation for AI is developed based on the Minimax algorithm with a few extra improvements including:
- Heuristic board evaluation based on pieces, position and check/mating possibilities
- Alpha- beta pruning
- Move ordering
- Transposition table for board states (memoization)
- Multiprocessing for multicore CPU utilization
  
<img src="https://github.com/Triksheim/TriksheimChess/assets/59808763/2d832b08-4806-4e44-a06c-040ff7972ead" width="800, height=400" >

<img src="https://github.com/Triksheim/TriksheimChess/assets/59808763/6878a31f-4cde-4050-981b-e67d1c9a86a2" width="800, height=400" >
