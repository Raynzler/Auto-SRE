import React from 'react';
import { Network, Database, Activity, AlertTriangle, Repeat, TrendingUp } from 'lucide-react';

export default function AutoSREArchitecture() {
  return (
    <div className="w-full h-full bg-slate-900 text-white p-8 overflow-auto">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">AutoSRE System Architecture</h1>
        <p className="text-slate-400 mb-8">Production-Ready SRE Demonstration Platform</p>

        {/* Architecture Layers */}
        <div className="space-y-6">
          
          {/* Layer 1: User Traffic */}
          <div className="bg-slate-800 rounded-lg p-6 border-l-4 border-blue-500">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Network className="w-5 h-5" />
              Layer 1: Traffic & Routing
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Nginx (Reverse Proxy)</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Rate limiting (10 req/sec/IP)</li>
                  <li>• Request timeout (5s)</li>
                  <li>• Access logs → Prometheus</li>
                  <li>• /metrics endpoint</li>
                </ul>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Load Simulator</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Constant load (5 RPS)</li>
                  <li>• Spike injection</li>
                  <li>• Failure scenario trigger</li>
                </ul>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Why This Layer?</h3>
                <p className="text-sm text-slate-300">
                  <strong className="text-yellow-400">SRE Principle:</strong> Rate limiting protects services from overload. Timeouts prevent cascading delays.
                </p>
              </div>
            </div>
          </div>

          {/* Layer 2: Application Services */}
          <div className="bg-slate-800 rounded-lg p-6 border-l-4 border-green-500">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Layer 2: Application Services
            </h2>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">API Service (FastAPI)</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li><strong>Endpoints:</strong></li>
                  <li>• GET /health (liveness)</li>
                  <li>• GET /ready (readiness)</li>
                  <li>• POST /orders</li>
                  <li>• GET /metrics</li>
                </ul>
                <div className="mt-3 p-2 bg-slate-800 rounded text-xs">
                  <strong>Failure Modes:</strong>
                  <br/>POST /chaos/latency (inject 2s delay)
                  <br/>POST /chaos/errors (50% failure rate)
                </div>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Worker Service (Python)</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li><strong>Responsibilities:</strong></li>
                  <li>• Process queue messages</li>
                  <li>• Retry with backoff (3 attempts)</li>
                  <li>• Dead-letter queue</li>
                  <li>• Emit processing metrics</li>
                </ul>
                <div className="mt-3 p-2 bg-slate-800 rounded text-xs">
                  <strong>Failure Modes:</strong>
                  <br/>Memory leak simulation
                  <br/>Slow processing (10s jobs)
                </div>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Auth Service (Go)</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li><strong>Responsibilities:</strong></li>
                  <li>• Token validation</li>
                  <li>• Circuit breaker to DB</li>
                  <li>• Fallback to cache</li>
                  <li>• 200ms SLO</li>
                </ul>
                <div className="mt-3 p-2 bg-slate-800 rounded text-xs">
                  <strong>Failure Modes:</strong>
                  <br/>DB connection loss
                  <br/>Cache miss storm
                </div>
              </div>
            </div>
            <div className="bg-slate-700 p-4 rounded">
              <h3 className="font-semibold mb-2 text-yellow-400">Why These Services?</h3>
              <p className="text-sm text-slate-300">
                <strong>API:</strong> Demonstrates request-based SLIs (latency, errors)
                <br/><strong>Worker:</strong> Shows async reliability patterns (retries, DLQ)
                <br/><strong>Auth:</strong> Critical dependency that needs circuit breaker + fallback
              </p>
            </div>
          </div>

          {/* Layer 3: Data & State */}
          <div className="bg-slate-800 rounded-lg p-6 border-l-4 border-purple-500">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Database className="w-5 h-5" />
              Layer 3: Data & State
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">PostgreSQL</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Single instance (acceptable for demo)</li>
                  <li>• Connection pooling (max 20)</li>
                  <li>• Health check query</li>
                  <li>• Slow query logging</li>
                </ul>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Redis</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Token cache (TTL: 5min)</li>
                  <li>• Rate limit counters</li>
                  <li>• Job queue (worker tasks)</li>
                  <li>• Circuit breaker state</li>
                </ul>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Why This Design?</h3>
                <p className="text-sm text-slate-300">
                  <strong className="text-yellow-400">SRE Principle:</strong> Redis as cache layer demonstrates graceful degradation. DB connection pooling prevents thundering herd.
                </p>
              </div>
            </div>
          </div>

          {/* Layer 4: Observability */}
          <div className="bg-slate-800 rounded-lg p-6 border-l-4 border-orange-500">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Layer 4: Observability Stack
            </h2>
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Prometheus</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Scrapes /metrics every 15s</li>
                  <li>• Retention: 15 days</li>
                  <li>• Recording rules for SLIs</li>
                </ul>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Grafana</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• RED dashboard per service</li>
                  <li>• SLO tracking dashboard</li>
                  <li>• Incident replay view</li>
                </ul>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Alertmanager</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Symptom-based alerts only</li>
                  <li>• Severity: P0/P1/P2</li>
                  <li>• Webhook to Slack/file</li>
                </ul>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Logging</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• JSON structured logs</li>
                  <li>• Request ID correlation</li>
                  <li>• Docker logs driver</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Layer 5: Self-Healing */}
          <div className="bg-slate-800 rounded-lg p-6 border-l-4 border-red-500">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Repeat className="w-5 h-5" />
              Layer 5: Self-Healing Mechanisms
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Docker Compose Policies</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• restart: unless-stopped</li>
                  <li>• healthcheck every 30s</li>
                  <li>• depends_on with conditions</li>
                  <li>• Resource limits (CPU/mem)</li>
                </ul>
              </div>
              <div className="bg-slate-700 p-4 rounded">
                <h3 className="font-semibold mb-2">Application-Level</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Circuit breaker (3 failures → open)</li>
                  <li>• Retry with exponential backoff</li>
                  <li>• Bulkhead pattern (thread pools)</li>
                  <li>• Graceful shutdown (SIGTERM)</li>
                </ul>
              </div>
            </div>
          </div>

          {/* SLI/SLO Definition */}
          <div className="bg-slate-800 rounded-lg p-6 border-l-4 border-cyan-500">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              SLI/SLO Framework
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-700">
                  <tr>
                    <th className="p-2 text-left">Service</th>
                    <th className="p-2 text-left">SLI</th>
                    <th className="p-2 text-left">SLO Target</th>
                    <th className="p-2 text-left">Alert Threshold</th>
                    <th className="p-2 text-left">Why This SLO?</th>
                  </tr>
                </thead>
                <tbody className="text-slate-300">
                  <tr className="border-t border-slate-700">
                    <td className="p-2">API Service</td>
                    <td className="p-2">Availability</td>
                    <td className="p-2">99.9% (30d)</td>
                    <td className="p-2">&lt;99.5% (5min)</td>
                    <td className="p-2">User-facing; needs high availability</td>
                  </tr>
                  <tr className="border-t border-slate-700">
                    <td className="p-2">API Service</td>
                    <td className="p-2">Latency (p95)</td>
                    <td className="p-2">&lt;500ms</td>
                    <td className="p-2">&gt;750ms (5min)</td>
                    <td className="p-2">User experience degrades above 500ms</td>
                  </tr>
                  <tr className="border-t border-slate-700">
                    <td className="p-2">Worker</td>
                    <td className="p-2">Processing Time</td>
                    <td className="p-2">&lt;5s (p99)</td>
                    <td className="p-2">&gt;10s (3min)</td>
                    <td className="p-2">Queue buildup risk above 5s</td>
                  </tr>
                  <tr className="border-t border-slate-700">
                    <td className="p-2">Auth Service</td>
                    <td className="p-2">Latency (p99)</td>
                    <td className="p-2">&lt;200ms</td>
                    <td className="p-2">&gt;300ms (2min)</td>
                    <td className="p-2">Blocks all requests; must be fast</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Implementation Priority */}
        <div className="mt-8 bg-gradient-to-r from-blue-900 to-purple-900 rounded-lg p-6">
          <h2 className="text-2xl font-bold mb-4">Implementation Phases</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-800 bg-opacity-50 p-4 rounded">
              <h3 className="font-semibold mb-2 text-blue-300">Phase 1: Foundation (Week 1)</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>✓ Docker Compose setup</li>
                <li>✓ API service + basic endpoints</li>
                <li>✓ Prometheus + Grafana</li>
                <li>✓ Health checks</li>
              </ul>
            </div>
            <div className="bg-slate-800 bg-opacity-50 p-4 rounded">
              <h3 className="font-semibold mb-2 text-green-300">Phase 2: Reliability (Week 2)</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>✓ Worker + Auth services</li>
                <li>✓ Circuit breakers</li>
                <li>✓ Alert definitions</li>
                <li>✓ First failure scenario</li>
              </ul>
            </div>
            <div className="bg-slate-800 bg-opacity-50 p-4 rounded">
              <h3 className="font-semibold mb-2 text-purple-300">Phase 3: Chaos (Week 3)</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>✓ All failure scenarios</li>
                <li>✓ Self-healing validation</li>
                <li>✓ Postmortems</li>
                <li>✓ Documentation</li>
              </ul>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}