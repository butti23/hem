// g++ -std=c++20 -O0 grasp.cpp -o grasp
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace std;
using Clock = chrono::steady_clock;
using Weight = int64_t;
struct Input {
    int n = 0;
    vector<pair<int,int>> edges;
    vector<Weight> weights;
};

Input read_input(const string& path, const string& weights_path) {
    Input g;
    ifstream in(path);
    if (!in) throw runtime_error("cannot read graph");
    int declared = -1;
    string line, tag, extra;
    while (getline(in,line)) {
        istringstream s(line);
        if (!(s >> tag) || tag == "c") continue;
        if (tag == "p") {
            string format;
            if (declared != -1 || !(s >> format >> g.n >> declared) ||
                format != "edge" || g.n < 1 || declared < 0 || (s >> extra))
                throw runtime_error("invalid graph header");
        } else {
            int a,b;
            if (tag != "e" || !(s >> a >> b) || (s >> extra) || a < 1 || b < 1 ||
                a > g.n || b > g.n || a == b) throw runtime_error("invalid edge");
            g.edges.emplace_back(min(a,b)-1,max(a,b)-1);
        }
    }
    if (declared < 0 || g.edges.size() != static_cast<size_t>(declared))
        throw runtime_error("edge count mismatch");
    g.weights.assign(g.n,1);
    if (weights_path != "-") {
        ifstream weights(weights_path);
        Weight total = 0;
        for (auto& w : g.weights) {
            if (!(weights >> w) || w < 0 || w > numeric_limits<Weight>::max()-total)
                throw runtime_error("invalid weights");
            total += w;
        }
        if (weights >> extra) throw runtime_error("extra weight");
    }
    return g;
}

struct Solution {
    vector<int> colors;
    Weight weight = 0;
};
struct Snapshot {
    double budget, elapsed;
    int restarts, moves;
    Solution best;
};

class Search {
    const Input& g;
    int k;
    Clock::time_point start;
    vector<double> budgets;
    double cutoff;
    mt19937 rng;
    vector<vector<int>> adj, product;
    vector<int> order;
    Solution best;
    int restarts = 0, moves = 0;
    vector<Snapshot> observations;

    double elapsed() const {
        return chrono::duration<double>(Clock::now()-start).count();
    }
    bool expired() const { return elapsed() >= cutoff; }
    void observe(double now) {
        while (observations.size() < budgets.size() && now >= budgets[observations.size()])
            observations.push_back({budgets[observations.size()],now,restarts,moves,best});
    }
    void publish(const Solution& current) {
        double now = elapsed();
        observe(now);
        if (now < cutoff && current.weight > best.weight) best = current;
    }
    Solution construct() {
        Solution s{vector<int>(g.n)};
        vector<char> active(product.size(),true);
        vector<int> degree;
        for (const auto& neighbors : product) degree.push_back(static_cast<int>(neighbors.size()));
        const auto remove = [&](int x) {
            if (!active[x]) return;
            active[x] = false;
            for (int y : product[x]) if (active[y]) --degree[y];
        };
        vector<double> priority(product.size());
        vector<int> rcl;
        while (!expired()) {
            double low = numeric_limits<double>::infinity(), high = -1;
            for (int x = 0; x < static_cast<int>(product.size()); ++x) if (active[x]) {
                priority[x] = static_cast<double>(g.weights[x/k])/(1+degree[x]);
                low = min(low,priority[x]);
                high = max(high,priority[x]);
            }
            if (high < 0) break;
            const double threshold = high - 0.2*(high-low);
            rcl.clear();
            for (int x = 0; x < static_cast<int>(product.size()); ++x)
                if (active[x] && priority[x] >= threshold) rcl.push_back(x);
            const int x = rcl[uniform_int_distribution<size_t>(0,rcl.size()-1)(rng)];
            s.colors[x/k] = x%k+1;
            s.weight += g.weights[x/k];
            publish(s);
            remove(x);
            for (int y : product[x]) remove(y);
        }
        return s;
    }
    void refill(Solution& s) {
        vector<char> blocked(k+1);
        for (int v : order) if (s.colors[v] == 0) {
            if (expired()) break;
            fill(blocked.begin(),blocked.end(),false);
            for (int u : adj[v]) blocked[s.colors[u]] = true;
            for (int j=1; j<=k; ++j) if (!blocked[j]) {
                s.colors[v] = j;
                s.weight += g.weights[v];
                break;
            }
        }
    }
    void local_search(Solution current) {
        while (!expired()) {
            refill(current);
            publish(current);
            Solution winner = current;
            for (int v=0; v<g.n && !expired(); ++v) if (current.colors[v]) {
                Solution trial = current;
                trial.colors[v] = 0;
                trial.weight -= g.weights[v];
                refill(trial);
                if (trial.weight > winner.weight) {
                    winner = move(trial);
                    publish(winner);
                }
            }
            if (winner.weight <= current.weight) return;
            current = move(winner);
            ++moves;
        }
    }
public:
    Search(Input& input,int colors,unsigned seed,const vector<double>& times,bool supervised)
      : g(input), k(colors), start(Clock::now()), budgets(times),
        cutoff(times.back()-(supervised ? min(0.025,times.back()/10) : 0)), rng(seed),
        adj(g.n), product(static_cast<size_t>(g.n)*k), order(g.n), best{vector<int>(g.n)} {
        sort(input.edges.begin(),input.edges.end());
        input.edges.erase(unique(input.edges.begin(),input.edges.end()),input.edges.end());
        for (auto [u,v] : g.edges) {
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        for (int v=0; v<g.n; ++v) for (int j=0; j<k; ++j) {
            auto& neighbors = product[v*k+j];
            for (int i=0; i<k; ++i) if (i!=j) neighbors.push_back(v*k+i);
            for (int u : adj[v]) neighbors.push_back(u*k+j);
        }
        iota(order.begin(),order.end(),0);
        stable_sort(order.begin(),order.end(),[&](int a,int b) {
            return static_cast<long double>(g.weights[a])/(1+adj[a].size()) >
                   static_cast<long double>(g.weights[b])/(1+adj[b].size());
        });
    }
    vector<Snapshot> run() {
        while (!expired()) {
            ++restarts;
            local_search(construct());
        }
        double end = elapsed();
        observe(end);
        while (observations.size() < budgets.size())
            observations.push_back({budgets[observations.size()],end,restarts,moves,best});
        return observations;
    }
};

#include "controls.hpp"

int main(int argc,char** argv) try {
    if (argc<6) throw runtime_error("usage: grasp graph.col weights|- k seed seconds [seconds ...]");
    auto input = read_input(argv[1],argv[2]);
    int k = stoi(argv[3]);
    if (k<1 || k>numeric_limits<int>::max()/input.n) throw runtime_error("invalid k");
    unsigned seed = stoul(argv[4]);
    vector<double> budgets;
    for (int i=5; i<argc; ++i) {
        double t = stod(argv[i]);
        if (!isfinite(t) || t<=0 || (!budgets.empty() && t<=budgets.back()))
            throw runtime_error("expected increasing positive budgets");
        budgets.push_back(t);
    }
    const bool supervised = getenv("HEM_SUPERVISED") != nullptr;
    if (supervised) {
        cout << "READY" << endl;
        string signal;
        if (!getline(cin,signal) || signal != "GO") throw runtime_error("missing start signal");
    }
    const char* configured_method = getenv("HEM_METHOD");
    string method = configured_method ? configured_method : "grasp";
    if (method!="grasp" && budgets.size()!=1)
        throw runtime_error("controls accept exactly one budget");
    auto results = method=="grasp" ? Search(input,k,seed,budgets,supervised).run()
                                  : Controls(input,k,budgets.back(),supervised).run(method);
    if (supervised) cout << "DONE" << endl;
    cout << setprecision(12) << "[";
    for (size_t i=0; i<results.size(); ++i) {
        const auto& r = results[i];
        if (i) cout << ",";
        cout << "{\"budget\":" << r.budget << ",\"elapsed\":" << r.elapsed
             << ",\"weight\":" << r.best.weight << ",\"restarts\":" << r.restarts
             << ",\"moves\":" << r.moves << ",\"colors\":[";
        for (size_t j=0; j<r.best.colors.size(); ++j)
            cout << (j ? "," : "") << r.best.colors[j];
        cout << "]}";
    }
    cout << "]\n";
} catch (const exception& e) {
    cerr << e.what() << "\n";
    return 1;
}
