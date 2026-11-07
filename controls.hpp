// Included after Input, Solution and Snapshot in grasp.cpp.
class Controls {
    Input& g;
    int k;
    Clock::time_point start = Clock::now();
    double budget, cutoff;
    vector<vector<int>> adj;
    int iterations = 0, improvements = 0;

    double elapsed() const {
        return chrono::duration<double>(Clock::now()-start).count();
    }
    bool expired() const { return elapsed() >= cutoff; }
    void check() const {
        if (expired()) throw runtime_error("control time limit before completion");
    }
    int available(const Solution& s,int v) const {
        vector<char> blocked(k+1,false);
        for (int u : adj[v]) blocked[s.colors[u]] = true;
        for (int j=1;j<=k;++j) if (!blocked[j]) return j;
        return 0;
    }
    void insert(Solution& s,int v) const {
        int color = available(s,v);
        if (color) {
            s.colors[v] = color;
            s.weight += g.weights[v];
        }
    }
    vector<int> degrees() const {
        vector<int> result;
        for (const auto& neighbors : adj) result.push_back(static_cast<int>(neighbors.size()));
        return result;
    }
    Solution briggs() {
        vector<int> degree = degrees(), stack;
        vector<char> active(g.n,true);
        while (stack.size()<static_cast<size_t>(g.n)) {
            check();
            int chosen = -1;
            for (int v=0;v<g.n;++v) if (active[v] && degree[v]<k) {
                chosen = v;
                break;
            }
            if (chosen<0) {
                for (int v=0;v<g.n;++v) if (active[v]) {
                    if (chosen<0 || static_cast<long double>(g.weights[v])/degree[v] <
                                   static_cast<long double>(g.weights[chosen])/degree[chosen])
                        chosen = v;
                }
            }
            stack.push_back(chosen);
            active[chosen] = false;
            for (int u : adj[chosen]) if (active[u]) --degree[u];
        }
        Solution s{vector<int>(g.n)};
        for (auto it=stack.rbegin();it!=stack.rend();++it) {
            check();
            insert(s,*it);
        }
        return s;
    }
    Solution independent() {
        const int count = g.n*k;
        vector<vector<int>> product(count);
        for (int v=0;v<g.n;++v) for (int j=0;j<k;++j) {
            for (int c=0;c<k;++c) if (c!=j) product[v*k+j].push_back(v*k+c);
            for (int u : adj[v]) product[v*k+j].push_back(u*k+j);
        }
        vector<char> active(count,true);
        vector<int> degree(count);
        for (int x=0;x<count;++x) degree[x]=static_cast<int>(product[x].size());
        Solution s{vector<int>(g.n)};
        const auto remove = [&](int x) {
            if (!active[x]) return;
            active[x]=false;
            for (int y : product[x]) if (active[y]) --degree[y];
        };
        while (true) {
            check();
            int chosen=-1;
            int64_t best_support=-1;
            for (int x=0;x<count;++x) if (active[x]) {
                int64_t support=0;
                for (int y : product[x]) if (active[y]) support+=degree[y];
                if (chosen<0 || degree[x]<degree[chosen] ||
                    (degree[x]==degree[chosen] && support>best_support)) {
                    chosen=x;
                    best_support=support;
                }
            }
            if (chosen<0) return s;
            s.colors[chosen/k]=chosen%k+1;
            s.weight+=g.weights[chosen/k];
            remove(chosen);
            for (int y : product[chosen]) remove(y);
        }
    }
    Solution adg() {
        auto degree=degrees();
        vector<char> active(g.n,true);
        vector<vector<int>> groups;
        int remaining=g.n;
        while (remaining) {
            check();
            int64_t sum=0;
            for (int v=0;v<g.n;++v) if (active[v]) sum+=degree[v];
            vector<int> group;
            for (int v=0;v<g.n;++v)
                if (active[v] && 10LL*degree[v]*remaining<=11LL*sum) group.push_back(v);
            for (int v : group) active[v]=false;
            for (int v : group) for (int u : adj[v]) if (active[u]) --degree[u];
            remaining-=static_cast<int>(group.size());
            groups.push_back(move(group));
        }
        Solution s{vector<int>(g.n)};
        for (auto it=groups.rbegin();it!=groups.rend();++it) for (int v : *it) {
            check();
            insert(s,v);
        }
        return s;
    }
    Solution tabu() {
        vector<int> order(g.n);
        iota(order.begin(),order.end(),0);
        stable_sort(order.begin(),order.end(),[&](int a,int b){return adj[a].size()<adj[b].size();});
        Solution s{vector<int>(g.n)};
        for (int j=1;j<=k;++j) for (int v : order) if (!s.colors[v]) {
            check();
            bool allowed=true;
            for (int u : adj[v]) if (s.colors[u]==j) allowed=false;
            if (allowed) {
                s.colors[v]=j;
                s.weight+=g.weights[v];
            }
        }
        Solution best=s;
        vector<int> protected_until(g.n,0);
        for (int t=1;t<=100000 && !expired();++t) {
            iterations=t;
            vector<int> discarded;
            for (int v : order) if (!s.colors[v]) discarded.push_back(v);
            if (discarded.empty()) return s;
            int chosen=-1, most=-1;
            for (int v=0;v<g.n;++v) if (s.colors[v] && protected_until[v]<=t) {
                int count=0;
                for (int u : adj[v]) if (!s.colors[u]) ++count;
                if (count>most) { chosen=v; most=count; }
            }
            if (chosen<0) continue;
            s.colors[chosen]=0;
            s.weight-=g.weights[chosen];
            discarded.push_back(chosen);
            for (int v : discarded) {
                if (expired()) return best;
                insert(s,v);
                if (s.colors[v]) protected_until[v]=t+8;
            }
            if (!expired() && s.weight>best.weight) {
                best=s;
                ++improvements;
            }
        }
        return best;
    }
public:
    Controls(Input& input,int colors,double seconds,bool supervised)
      : g(input),k(colors),budget(seconds),
        cutoff(seconds-(supervised ? min(0.025,seconds/10) : 0)),adj(g.n) {
        sort(g.edges.begin(),g.edges.end());
        g.edges.erase(unique(g.edges.begin(),g.edges.end()),g.edges.end());
        for (auto [u,v] : g.edges) {
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }
    vector<Snapshot> run(const string& method) {
        Solution result;
        if (method=="briggs") result=briggs();
        else if (method=="mis") result=independent();
        else if (method=="adg") result=adg();
        else if (method=="tabu") result=tabu();
        else throw runtime_error("unknown control");
        return {{budget,elapsed(),iterations,improvements,move(result)}};
    }
};
