<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '@/api/client'

const snapshot = ref(null)
const error = ref('')
const commandBusy = ref(false)
let pollTimer

const inputRows = [
  ['temperature_c', 'Temperature PV', '°C'],
  ['pressure_torr', 'Pressure PV', 'torr'],
  ['diameter_mm', 'Diameter PV', 'mm'],
  ['pull_speed_mm_min', 'Pull Speed PV', 'mm/min'],
  ['argon_flow_slm', 'Argon Flow PV', 'slm'],
  ['crucible_position_mm', 'Crucible Position', 'mm'],
]

const outputRows = [
  ['heater_output_pct', 'Heater Output', '%'],
  ['pull_speed_mm_min', 'Pull Speed Output', 'mm/min'],
  ['argon_valve_pct', 'Argon Valve', '%'],
  ['vacuum_pump_pct', 'Vacuum Pump', '%'],
  ['crucible_speed_rpm', 'Crucible Speed', 'rpm'],
  ['seed_rotation_rpm', 'Seed Rotation', 'rpm'],
  ['cooling_output_pct', 'Cooling Output', '%'],
]

const stateClass = computed(() => {
  const state = snapshot.value?.state
  if (state === 'RUNNING') return 'ok'
  if (state === 'FAULT' || state === 'DISCONNECTED') return 'danger'
  if (state === 'STOPPED') return 'warn'
  return 'dim'
})

function formatValue(value) {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toString() : value.toFixed(2)
  }
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE'
  return value ?? '—'
}

async function refresh() {
  try {
    snapshot.value = await api.plcStatus()
    error.value = ''
  } catch (e) {
    error.value = e.message || 'PLC 狀態讀取失敗'
  }
}

async function sendCommand(command) {
  commandBusy.value = true
  error.value = ''
  try {
    snapshot.value = await api.plcCommand(command)
  } catch (e) {
    error.value = e.message || `${command} 指令失敗`
  } finally {
    commandBusy.value = false
  }
}

onMounted(async () => {
  await refresh()
  pollTimer = window.setInterval(refresh, 1000)
})

onBeforeUnmount(() => window.clearInterval(pollTimer))
</script>

<template>
  <section>
    <div class="page-head runtime-head">
      <div>
        <h2>Virtual PLC Runtime</h2>
        <p>Plant Simulator → OPC UA I/O → PLC interlocks / sequence / control → DCS</p>
      </div>
      <div class="controls runtime-controls">
        <button
          class="btn primary"
          :disabled="commandBusy || !snapshot?.enabled || snapshot?.state === 'RUNNING'"
          @click="sendCommand('start')"
        >
          START
        </button>
        <button
          class="btn"
          :disabled="commandBusy || !snapshot?.enabled"
          @click="sendCommand('stop')"
        >
          STOP
        </button>
        <button
          class="btn"
          :disabled="commandBusy || !snapshot?.enabled"
          @click="sendCommand('reset')"
        >
          RESET
        </button>
      </div>
    </div>

    <div v-if="error" class="runtime-error">⚠ {{ error }}</div>

    <div v-if="!snapshot" class="loading">讀取 PLC Runtime…</div>

    <template v-else>
      <div class="stat-row">
        <div class="stat">
          <div class="label">PLC State</div>
          <div class="value state-value">
            <span class="badge" :class="stateClass">{{ snapshot.state }}</span>
          </div>
          <div class="sub">{{ snapshot.enabled ? 'Runtime enabled' : 'Set PLC_RUNTIME_ENABLED=true' }}</div>
        </div>
        <div class="stat">
          <div class="label">OPC UA</div>
          <div class="value">{{ snapshot.connected ? 'ONLINE' : 'OFFLINE' }}</div>
          <div class="sub">Plant Simulator connection</div>
        </div>
        <div class="stat">
          <div class="label">Process Phase</div>
          <div class="value">{{ snapshot.inputs.plant_phase }}</div>
          <div class="sub">Mode {{ snapshot.inputs.plant_mode }}</div>
        </div>
        <div class="stat">
          <div class="label">Scan Time</div>
          <div class="value">{{ formatValue(snapshot.scan_time_ms) }} ms</div>
          <div class="sub">{{ snapshot.cycle_count.toLocaleString() }} scans</div>
        </div>
      </div>

      <div class="runtime-grid">
        <article class="card">
          <h3>Plant → PLC Input Image</h3>
          <table>
            <thead>
              <tr><th>Tag</th><th>Value</th><th>Unit</th></tr>
            </thead>
            <tbody>
              <tr v-for="[key, label, unit] in inputRows" :key="key">
                <td>{{ label }}</td>
                <td class="num">{{ formatValue(snapshot.inputs[key]) }}</td>
                <td class="muted">{{ unit }}</td>
              </tr>
            </tbody>
          </table>
        </article>

        <article class="card">
          <h3>PLC → Plant Output Image</h3>
          <table>
            <thead>
              <tr><th>Tag</th><th>Value</th><th>Unit</th></tr>
            </thead>
            <tbody>
              <tr v-for="[key, label, unit] in outputRows" :key="key">
                <td>{{ label }}</td>
                <td class="num">{{ formatValue(snapshot.outputs[key]) }}</td>
                <td class="muted">{{ unit }}</td>
              </tr>
            </tbody>
          </table>
        </article>
      </div>

      <div class="runtime-grid lower-grid">
        <article class="card">
          <h3>Safety Interlocks</h3>
          <div class="interlock-list">
            <div v-for="item in snapshot.interlocks" :key="item.key" class="interlock">
              <span class="indicator" :class="{ healthy: item.healthy }" />
              <span>{{ item.label }}</span>
              <span class="badge" :class="item.healthy ? 'ok' : 'danger'">
                {{ item.healthy ? 'HEALTHY' : 'TRIPPED' }}
              </span>
            </div>
          </div>
          <div class="permit-row">
            Interlock Permit
            <strong :class="snapshot.outputs.interlock_permit ? 'ok-text' : 'danger-text'">
              {{ snapshot.outputs.interlock_permit ? 'PERMITTED' : 'BLOCKED' }}
            </strong>
          </div>
        </article>

        <article class="card">
          <h3>Active Alarms</h3>
          <div v-if="snapshot.alarms.length === 0" class="empty compact">No active alarms</div>
          <div v-else class="alarm-list">
            <div v-for="alarm in snapshot.alarms" :key="alarm" class="alarm">⚠ {{ alarm }}</div>
          </div>
          <div v-if="snapshot.last_scan_at" class="last-scan mono">
            Last scan {{ new Date(snapshot.last_scan_at).toLocaleString() }}
          </div>
        </article>
      </div>
    </template>
  </section>
</template>

<style scoped>
.runtime-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
}
.runtime-controls {
  margin-bottom: 0;
}
.runtime-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
}
.lower-grid {
  align-items: stretch;
}
.state-value {
  margin: 9px 0 7px !important;
}
.state-value .badge {
  font-family: inherit;
  font-size: 13px;
  letter-spacing: 0.5px;
}
.runtime-error,
.alarm {
  color: var(--danger);
  border: 1px solid color-mix(in srgb, var(--danger) 35%, transparent);
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  border-radius: 6px;
  padding: 8px 10px;
}
.runtime-error {
  margin-bottom: 14px;
}
.interlock-list,
.alarm-list {
  display: grid;
  gap: 8px;
}
.interlock {
  display: grid;
  grid-template-columns: 9px 1fr auto;
  align-items: center;
  gap: 9px;
  min-height: 29px;
}
.indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--danger);
}
.indicator.healthy {
  background: var(--ok);
  box-shadow: 0 0 8px color-mix(in srgb, var(--ok) 55%, transparent);
}
.permit-row {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--border);
  margin-top: 13px;
  padding-top: 12px;
}
.ok-text {
  color: var(--ok);
}
.danger-text {
  color: var(--danger);
}
.compact {
  padding: 28px 10px;
}
.last-scan {
  color: var(--text-faint);
  font-size: 10.5px;
  margin-top: 14px;
}
tbody tr {
  cursor: default;
}
@media (max-width: 900px) {
  .runtime-grid {
    grid-template-columns: 1fr;
  }
  .runtime-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
