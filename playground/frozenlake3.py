import gymnasium as gym

env = gym.make(
    "FrozenLake-v1",
    map_name="4x4",
    is_slippery=True,
    success_rate=1.0 / 3.0,
    reward_schedule=(1, 0, 0),
    render_mode=None         # no ANSI rendering needed for this dump
)

# Human-friendly action names
ACTIONS = ["LEFT", "DOWN", "RIGHT", "UP"]

def print_state_transitions(environment):
    """Pretty-print the full state-transition table of a FrozenLake env."""
    P = environment.unwrapped.P          # {state: {action: [(p, s', r, term, trunc), …]}}
    for state in range(environment.observation_space.n):
        # print(f"\nState {state}:")
        # for action in range(environment.action_space.n):
        #     for prob, next_state, reward, truncated in P[state][action]:
        #         done = truncated
        #         print(
        #             f"  └─ action {action} ({ACTIONS[action]:>4}) "
        #             f"→ next_state {next_state:2d}  "
        #             f"prob={prob:.2f}  reward={reward}  done={done}"
        #         )

        print(f"\n// State {state}:")
        print("std::array{")
        for action in range(environment.action_space.n):
            print("\tstd::vector{", end="")
            for prob, next_state, reward, truncated in P[state][action]:
                print("ASResult_t{", end="")
                done = truncated
                print(prob, end=", ")
                print(reward, end=", ")
                print(next_state, end=", ")
                if done:
                    print("true", end="}, ")
                else:
                    print("false", end="}, ")
            print("},")
        print("\t},")



print_state_transitions(env)
