"""
Comprehensive Markov-based Intraday Trading Toolkit
File: markov_intraday_full.py

Features included:
1. Basic 1-step Markov Chain model (states: UP/FLAT/DOWN)
2. N-step Markov Chain
3. Hidden Markov Model (HMM) regime detection using hmmlearn (optional)
4. Backtesting engine (entry/exit, P&L, equity curve, metrics)
5. Simple Reinforcement Learning (Q-learning) agent using discrete Markov states
6. Combine Markov predictions with Moving Average filter
7. Full trading bot simulation with entry/exit rules

Usage:
python markov_intraday_full.py --file intraday.csv --mode all

Modes: basic, nstep, hmm, backtest, rl_train, combined, bot, all

CSV format expected:
timestamp,open,high,low,close,volume
timestamp should be parseable by pandas.to_datetime

Dependencies:
- pandas
- numpy
- scikit-learn (optional for preprocessing)
- hmmlearn (optional for HMM)

Install optional deps:
pip install pandas numpy scikit-learn hmmlearn

This script is designed for clarity and teaching. Adapt thresholds and hyperparameters to your dataset.
"""

import argparse
import pandas as pd
import numpy as np
from collections import defaultdict, deque
import math
import pickle
from Data.fyers_data_final import *

scanner = FyersDataScanner()
scanner.start_date ='2025-11-18 16:15:00'
scanner.end_date = '2025-11-20 16:15:00'
scanner.symbol = 'BSE:SENSEX25N2084600CE'
scanner.resolution = '5S'
            


try:
    from hmmlearn.hmm import GaussianHMM
    HMM_AVAILABLE = True
except Exception: 
    HMM_AVAILABLE = False

# ---------------------- Utility functions ----------------------

def load_data(filename=None, datetime_col='timestamp'):
    # df = pd.read_csv(filename, parse_dates=[datetime_col])
    df = scanner.get_data()
    ndf = df[['datetime','Open','Close','High','Low','Vol','TradeVol']].copy()
    # timestamp,open,high,low,close,volume
    ndf.rename(columns={'Vol':'volume','datetime':'timestamp','Open':'open','Close':'close','High':'high','Low':'low','TradeVol':'trade_volume'},inplace=True)
    ndf = ndf.sort_values(datetime_col).reset_index(drop=True)
    return ndf


def compute_returns(df):
    df = df.copy()
    df['return'] = df['close'].pct_change()
    return df


# ---------------------- State generation ----------------------

def get_state_simple(ret, up=0.001, down=-0.001):
    # thresholds are relative returns (e.g., 0.001 = 0.1%)
    if np.isnan(ret):
        return None
    if ret > up:
        return 'U'
    elif ret < down:
        return 'D'
    return 'F'


def add_states(df, up=0.001, down=-0.001):
    df = df.copy()
    df = compute_returns(df)
    df['state'] = df['return'].apply(lambda r: get_state_simple(r, up, down))
    df = df.dropna(subset=['state']).reset_index(drop=True)
    return df


# ---------------------- 1-step Markov ----------------------

def build_transition_matrix(states_seq, state_labels=['U','F','D']):
    # states_seq: list/Series of states
    labels = state_labels
    matrix = pd.DataFrame(0, index=labels, columns=labels, dtype=float)
    for i in range(1, len(states_seq)):
        prev_s = states_seq[i-1]
        cur_s = states_seq[i]
        if prev_s in labels and cur_s in labels:
            matrix.loc[prev_s, cur_s] += 1
    # normalize rows
    matrix = matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0)
    return matrix


def predict_next_state_prob(matrix, current_state):
    if current_state not in matrix.index:
        return None
    return matrix.loc[current_state].to_dict()


# ---------------------- N-step Markov ----------------------

def build_nstep_transitions(states_seq, N=3):
    transitions = {}
    seqs = []
    for i in range(N, len(states_seq)):
        prev = ''.join(states_seq[i-N:i])
        nxt = states_seq[i]
        if prev not in transitions:
            transitions[prev] = defaultdict(int)
        transitions[prev][nxt] += 1
    # convert counts to probabilities
    for prev in transitions:
        total = float(sum(transitions[prev].values()))
        for k in transitions[prev]:
            transitions[prev][k] /= total
    return transitions


# ---------------------- Hidden Markov Model ----------------------

def train_hmm(df, n_components=3, features=['return','vol']):
    if not HMM_AVAILABLE:
        raise RuntimeError('hmmlearn is not installed. pip install hmmlearn to use HMM features.')
    df2 = df.copy()
    df2['return'] = df2['close'].pct_change()
    df2['vol'] = df2['return'].rolling(10).std().fillna(0)
    df2 = df2.dropna().reset_index(drop=True)
    X = df2[features].values
    model = GaussianHMM(n_components=n_components, covariance_type='full', n_iter=200)
    model.fit(X)
    states = model.predict(X)
    df2['hmm_state'] = states
    return model, df2


# ---------------------- Backtesting Engine ----------------------

class BacktestResult:
    def __init__(self):
        self.trades = []
        self.equity = []


def compute_metrics(equity_curve):
    # equity_curve: Series of cumulative returns (starting at 1)
    returns = equity_curve.pct_change().fillna(0)
    total_return = equity_curve.iloc[-1] - 1.0
    # annualize factor: intraday depends — assume 252 trading days, 390 minutes/day if 1-min bars
    # annual_factor = 252 * 390
    annual_factor = 252 * 4680
    avg_ret = returns.mean()
    vol = returns.std() * math.sqrt(annual_factor)
    sharpe = (avg_ret * annual_factor) / vol if vol != 0 else np.nan
    # max drawdown
    cum = equity_curve
    high = cum.cummax()
    drawdown = (cum - high) / high
    max_dd = drawdown.min()
    return {
        'total_return': float(total_return),
        'sharpe_est': float(sharpe),
        'max_drawdown': float(max_dd)
    }


def backtest_signals(df, signals, init_cash=100000, slippage=0.0, fee=0.0):
    # signals: Series aligned with df index: 1 = long, -1 = short, 0 = flat
    df = df.copy().reset_index(drop=True)
    cash = init_cash
    position = 0.0
    pos_price = 0.0
    equity_list = []
    positions = []
    for i, row in df.iterrows():
        price = row['close']
        sig = signals.iloc[i]
        # very simple execution: assume full position size when signal 1 or -1
        target_pos = 0.0
        if sig == 1:
            target_pos = cash * 0.1 / price  # risk allocation: 10% of cash as position
        elif sig == -1:
            target_pos = -cash * 0.1 / price
        # execute: for simplicity close old pos and open new
        if position != 0 and np.sign(position) != np.sign(target_pos):
            # close
            cash += position * price - abs(position) * fee - abs(position) * slippage
            position = 0.0
        if position == 0 and target_pos != 0:
            position = target_pos
            cash -= position * price + abs(position) * fee + abs(position) * slippage
            pos_price = price
        # update equity
        equity = cash + position * price
        equity_list.append(equity)
        positions.append(position)
    equity_curve = pd.Series(equity_list, index=df.index)
    metrics = compute_metrics(equity_curve / equity_curve.iloc[0])
    return equity_curve, metrics


# ---------------------- Simple RL Agent (Q-Learning) ----------------------

class QAgent:
    def __init__(self, states, actions=[-1,0,1], alpha=0.1, gamma=0.99, eps=0.1):
        # states: iterable of observed discrete states strings
        self.actions = actions
        self.alpha = alpha
        self.gamma = gamma
        self.eps = eps
        self.Q = defaultdict(lambda: {a: 0.0 for a in self.actions})

    def choose(self, state):
        # epsilon-greedy
        if np.random.rand() < self.eps:
            return np.random.choice(self.actions)
        qvals = self.Q[state]
        best = max(qvals, key=lambda a: qvals[a])
        return best

    def update(self, s, a, r, s2):
        q = self.Q[s][a]
        q_next = max(self.Q[s2].values()) if s2 in self.Q else 0.0
        self.Q[s][a] = q + self.alpha * (r + self.gamma * q_next - q)

    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump(dict(self.Q), f)

    def load(self, path):
        with open(path, 'rb') as f:
            data = pickle.load(f)
        self.Q = defaultdict(lambda: {a: 0.0 for a in self.actions}, data)


def train_q_agent(df, N=3, episodes=50):
    # Build N-step sequences as states
    df2 = add_states(df)
    states = df2['state'].values
    sequences = [''.join(states[i-N+1:i+1]) for i in range(N-1, len(states))]
    prices = df2['close'].values[N-1:]

    agent = QAgent(states=set(sequences))

    for ep in range(episodes):
        cash = 100000
        pos = 0
        for t in range(len(sequences)-1):
            s = sequences[t]
            a = agent.choose(s)
            price = prices[t]
            # execute simplistic: position unit 1
            reward = 0
            # compute next price diff as reward
            next_price = prices[t+1]
            reward = (next_price - price) * (a)  # if a==1 long, -1 short
            s2 = sequences[t+1]
            agent.update(s, a, reward, s2)
    return agent


# ---------------------- Combine with Moving Average ----------------------

def generate_ma_filter_signals(df, short=5, long=20):
    df = df.copy()
    df['ma_short'] = df['close'].rolling(short).mean()
    df['ma_long'] = df['close'].rolling(long).mean()
    df['ma_sig'] = 0
    df.loc[df['ma_short'] > df['ma_long'], 'ma_sig'] = 1
    df.loc[df['ma_short'] < df['ma_long'], 'ma_sig'] = -1
    df['ma_sig'] = df['ma_sig'].fillna(0)
    return df['ma_sig']


# ---------------------- Full Trading Bot (Simulation) ----------------------

def full_bot_simulation(df, markov_matrix=None, nstep_trans=None, N=3, ma_short=5, ma_long=20,
                        p_thresh=0.6):
    # Generate signals combining Markov prediction and MA filter
    df2 = add_states(df)
    sigs = pd.Series(0, index=df2.index)
    # compute ma filter
    ma_sig = generate_ma_filter_signals(df)
    ma_sig = ma_sig.loc[df2.index].fillna(0)

    if nstep_trans is not None:
        states = df2['state'].values
        for i in range(N, len(states)):
            cur_seq = ''.join(states[i-N:i])
            probs = nstep_trans.get(cur_seq, None)
            ma = ma_sig.iloc[i]
            if probs:
                # choose highest next-state prob
                p_up = probs.get('U', 0)
                p_down = probs.get('D', 0)
                if p_up > p_thresh and ma == 1:
                    sigs.iloc[i] = 1
                elif p_down > p_thresh and ma == -1:
                    sigs.iloc[i] = -1
    elif markov_matrix is not None:
        states = df2['state'].values
        for i in range(1, len(states)):
            cur = states[i-1]
            probs = predict_next_state_prob(markov_matrix, cur)
            ma = ma_sig.iloc[i]
            if probs:
                if probs.get('U',0) > p_thresh and ma == 1:
                    sigs.iloc[i] = 1
                elif probs.get('D',0) > p_thresh and ma == -1:
                    sigs.iloc[i] = -1
    else:
        raise ValueError('Provide either markov_matrix or nstep_trans')

    equity, metrics = backtest_signals(df2, sigs)
    return equity, metrics, sigs


# ---------------------- Main interactive orchestration ----------------------

def main(args):
    df = load_data()

    if args.mode in ('basic','all'):
        print('\n=== BASIC 1-step MARKOV ===')
        df_states = add_states(df)
        mat = build_transition_matrix(df_states['state'].values)
        print(mat)
        cur = df_states['state'].iloc[-1]
        print('Current state:', cur)
        print('Next probs:', predict_next_state_prob(mat, cur))

    if args.mode in ('nstep','all'):
        print('\n=== N-STEP MARKOV (N=%d) ===' % args.N)
        df_states = add_states(df)
        ntrans = build_nstep_transitions(df_states['state'].values, N=args.N)
        sample_keys = list(ntrans.keys())[:5]
        print('Sample sequences:', sample_keys)
        for k in sample_keys:
            print(k, '->', ntrans[k])

    if args.mode in ('hmm','all'):
        print('\n=== HIDDEN MARKOV MODEL ===')
        if not HMM_AVAILABLE:
            print('hmmlearn not available. Skip HMM. pip install hmmlearn to enable')
        else:
            model, dfh = train_hmm(df, n_components=args.hmm_states)
            print('Trained HMM with %d states' % args.hmm_states)
            print(dfh[['hmm_state']].tail(10))

    if args.mode in ('backtest','all'):
        print('\n=== BACKTEST SIMPLE MARKOV STRATEGY ===')
        df_states = add_states(df)
        mat = build_transition_matrix(df_states['state'].values)
        # generate signals based on basic markov
        sigs = pd.Series(0, index=df_states.index)
        for i in range(1, len(df_states)):
            cur = df_states['state'].iloc[i-1]
            probs = predict_next_state_prob(mat, cur)
            if probs:
                if probs.get('U',0) > args.p_thresh:
                    sigs.iloc[i] = 1
                elif probs.get('D',0) > args.p_thresh:
                    sigs.iloc[i] = -1
        equity, metrics = backtest_signals(df_states, sigs)
        print('Backtest metrics:', metrics)

    if args.mode in ('rl_train','all'):
        print('\n=== RL Q-LEARNING TRAINING ===')
        agent = train_q_agent(df, N=args.N, episodes=args.episodes)
        agent.save('qagent.pkl')
        print('Trained Q-agent saved to qagent.pkl')

    if args.mode in ('combined','all'):
        print('\n=== COMBINED N-STEP MARKOV + MA BOT ===')
        df_states = add_states(df)
        ntrans = build_nstep_transitions(df_states['state'].values, N=args.N)
        equity, metrics, sigs = full_bot_simulation(df, nstep_trans=ntrans, N=args.N,
                                                   ma_short=args.ma_short, ma_long=args.ma_long,
                                                   p_thresh=args.p_thresh)
        print('Combined bot metrics:', metrics)

    if args.mode in ('bot','all'):
        print('\n=== FULL BOT (1-step Markov + MA) ===')
        df_states = add_states(df)
        mat = build_transition_matrix(df_states['state'].values)
        equity, metrics, sigs = full_bot_simulation(df, markov_matrix=mat,
                                                   ma_short=args.ma_short, ma_long=args.ma_long,
                                                   p_thresh=args.p_thresh)
        print('Full bot metrics:', metrics)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True, help='Intraday CSV file')
    parser.add_argument('--mode', default='all', choices=['basic','nstep','hmm','backtest','rl_train','combined','bot','all'])
    parser.add_argument('--N', type=int, default=3, help='N for N-step Markov / RL state length')
    parser.add_argument('--p_thresh', type=float, default=0.6, help='Probability threshold for signals')
    parser.add_argument('--hmm_states', type=int, default=3, help='HMM components')
    parser.add_argument('--ma_short', type=int, default=5)
    parser.add_argument('--ma_long', type=int, default=20)
    parser.add_argument('--episodes', type=int, default=50)
    args = parser.parse_args()
    main(args)
