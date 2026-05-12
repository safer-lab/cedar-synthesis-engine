"""Terminal UI + persistence for cedar_agent.

Real interactive UI lives in ``terminal.py`` (Step C). The
``persistence.py`` helper writes session state to JSON so an
interrupted session can resume; per HITL_STEP_B_PLAN §7.1, resume is
mandatory for the ~30-minute user-attention budget.
"""
