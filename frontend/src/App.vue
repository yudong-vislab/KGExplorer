<script setup>
import { ref } from 'vue';
import KnowledgeGraphView from './components/KnowledgeGraphView.vue';

const globalTabs = ref([
  { id: 'global', title: 'Global KG', active: true },
  { id: 'overview', title: 'Overview', active: false },
]);

const derivedTabs = ref([
  { id: 'derived', title: 'Derived KG', active: true },
  { id: 'evidence', title: 'Result KG', active: false },
]);

const messages = ref([
  { role: 'assistant', text: 'Select a folder or graph node to inspect related entities.' },
]);
const draft = ref('');

function activateTab(tabs, id) {
  tabs.value = tabs.value.map((tab) => ({ ...tab, active: tab.id === id }));
}

function closeTab(tabs, id) {
  if (tabs.value.length === 1) return;
  const closingActive = tabs.value.find((tab) => tab.id === id)?.active;
  tabs.value = tabs.value.filter((tab) => tab.id !== id);
  if (closingActive) tabs.value[0].active = true;
}

function sendMessage() {
  const text = draft.value.trim();
  if (!text) return;
  messages.value.push({ role: 'user', text });
  messages.value.push({ role: 'assistant', text: 'LLM placeholder: this panel is ready for the Flask /api/chat endpoint.' });
  draft.value = '';
}
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <h1>KGExplorer: Knowledge Graph Visual Analytics System</h1>
    </header>

    <section class="workspace" aria-label="Main workspace">
      <aside class="panel left-panel" aria-label="Workspace panel">
        <header class="panel-title">KG Workspace</header>

        <div class="left-content">
          <section class="control-card folder-card" aria-label="Folder hierarchy">
            <h2>Knowledge Folders</h2>
            <div class="folder-toolbar">
              <button type="button">Open</button>
              <button type="button">Sync</button>
            </div>
            <ul class="folder-tree">
              <li class="open">
                <span class="folder-name">wiki</span>
                <ul>
                  <li class="open">
                    <span class="folder-name">concepts</span>
                    <ul>
                      <li><span>field</span></li>
                      <li><span>method</span></li>
                      <li><span>phenomenon</span></li>
                      <li><span>theory</span></li>
                    </ul>
                  </li>
                  <li class="open">
                    <span class="folder-name">entities</span>
                    <ul>
                      <li><span>event</span></li>
                      <li><span>organization</span></li>
                      <li><span>person</span></li>
                      <li><span>product</span></li>
                      <li><span>project</span></li>
                    </ul>
                  </li>
                  <li><span>raw</span></li>
                  <li><span>schema</span></li>
                  <li><span>sources</span></li>
                </ul>
              </li>
            </ul>
          </section>

          <section class="chat-zone control-card" aria-label="LLM dialog placeholder">
            <h2>LLM Dialog</h2>
            <div class="messages">
              <article v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
                {{ message.text }}
              </article>
            </div>
            <form class="chat-input" @submit.prevent="sendMessage">
              <input v-model="draft" placeholder="Ask a question about the knowledge graph..." />
              <button type="submit">Send</button>
            </form>
          </section>
        </div>
      </aside>

      <section class="panel center-panel" aria-label="Main visualization view">
        <header class="panel-toolbar">
          <h2>KG Exploration View</h2>
          <div class="mode-switch">
            <button type="button">Single Select</button>
            <button type="button">Multiple Select</button>
            <button type="button">Area Select</button>
          </div>
          <button class="save-button" type="button">Save</button>
        </header>
        <div class="graph-workbench">
          <section class="graph-pane" aria-label="Global knowledge graph">
            <div class="browser-tabs">
              <button
                v-for="tab in globalTabs"
                :key="tab.id"
                :class="['browser-tab', { active: tab.active }]"
                type="button"
                @click="activateTab(globalTabs, tab.id)"
              >
                <span>{{ tab.title }}</span>
                <i @click.stop="closeTab(globalTabs, tab.id)">×</i>
              </button>
              <button class="new-tab" type="button">＋</button>
            </div>
            <KnowledgeGraphView variant="global" />
          </section>

          <section class="graph-pane" aria-label="Interaction-derived knowledge graph">
            <div class="browser-tabs">
              <button
                v-for="tab in derivedTabs"
                :key="tab.id"
                :class="['browser-tab', { active: tab.active }]"
                type="button"
                @click="activateTab(derivedTabs, tab.id)"
              >
                <span>{{ tab.title }}</span>
                <i @click.stop="closeTab(derivedTabs, tab.id)">×</i>
              </button>
              <button class="new-tab" type="button">＋</button>
            </div>
            <KnowledgeGraphView variant="derived" />
          </section>
        </div>
      </section>

      <aside class="panel right-panel blank-panel" aria-label="Blank placeholder">
        <header class="panel-title">Reserved Panel</header>
        <div class="blank-placeholder"></div>
      </aside>
    </section>
  </main>
</template>
