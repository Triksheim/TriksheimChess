# Chess game with AI engine
Chess logic and engine is written in Python. GUI made with Pygame. 

### Run main.py to play

Can choose between Player or AI for both side selections making it possible to play:  
Player vs AI, Player vs Player or AI vs AI.  
AI can be set to three different difficulty levels.

The move generation for AI is developed based on the Minimax algorithm with a few extra improvements including:
- Heuristic board evaluation based on pieces, position and check/mating possibilities.
- Alpha- beta pruning.
- Move ordering.
- Tree search depth extensions for interestning moves.
- Transposition table for board states (memoization).
- Multiprocessing for multicore CPU utilization.
  

<img src="https://github.com/Triksheim/TriksheimChess/assets/59808763/b0ff08b4-0e9c-40c9-aa36-a5bb5e176942" width="800, height=400" >
