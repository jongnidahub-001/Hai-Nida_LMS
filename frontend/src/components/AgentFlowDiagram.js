import React, { useState, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// ============== Custom Node Components ==============

const AgentNode = ({ data }) => {
  const { label, icon, color, status, onClick, isSelected, tokenUsage } = data;
  const statusColors = { done: '#10b981', error: '#ef4444', pending: '#d1d5db' };

  return (
    <div
      onClick={onClick}
      style={{
        padding: '10px 14px',
        borderRadius: '12px',
        border: isSelected ? `2.5px solid ${color}` : '1.5px solid #e5e7eb',
        backgroundColor: isSelected ? `${color}12` : 'white',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        boxShadow: isSelected ? `0 4px 14px ${color}30` : '0 2px 8px rgba(0,0,0,0.06)',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        minWidth: '155px',
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: '#9ca3af', width: '6px', height: '6px' }} />
      <div style={{
        width: '32px', height: '32px', borderRadius: '50%',
        backgroundColor: `${color}15`, display: 'flex',
        alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <i className={icon} style={{ color, fontSize: '0.85rem' }}></i>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: '0.72rem', fontWeight: '500', color: '#374151', lineHeight: '1.3', display: 'block' }}>
          {label}
        </span>
        {tokenUsage && tokenUsage.total_tokens > 0 && (
          <span style={{ fontSize: '0.62rem', color: '#9ca3af', display: 'block', marginTop: '2px' }}>
            <i className="fas fa-coins" style={{ marginRight: '3px', fontSize: '0.55rem' }}></i>
            {tokenUsage.total_tokens.toLocaleString()} tokens
          </span>
        )}
      </div>
      <span style={{
        width: '10px', height: '10px', borderRadius: '50%',
        backgroundColor: statusColors[status] || statusColors.pending, flexShrink: 0,
      }}></span>
      <Handle type="source" position={Position.Right} style={{ background: '#9ca3af', width: '6px', height: '6px' }} />
    </div>
  );
};

const GroupNode = ({ data }) => {
  return (
    <div style={{
      padding: '8px',
      borderRadius: '14px',
      border: '2px dashed #c4b5fd',
      backgroundColor: '#faf5ff',
      minWidth: data.width || 180,
      minHeight: data.height || 100,
    }}>
      <div style={{
        fontSize: '0.7rem', fontWeight: '700', color: '#7c3aed',
        textTransform: 'uppercase', letterSpacing: '0.03em',
        marginBottom: '4px', paddingLeft: '4px',
      }}>
        {data.label}
      </div>
    </div>
  );
};

const nodeTypes = { agent: AgentNode, group: GroupNode };

// ============== Helper Functions ==============

function getNodeIcon(agentName) {
  const name = agentName?.toLowerCase() || '';
  if (name.includes('planner') && !name.includes('reviewer')) return 'fas fa-sitemap';
  if (name.includes('outline_reviewer') || name.includes('planner_reviewer')) return 'fas fa-clipboard-check';
  if (name.includes('writer')) return 'fas fa-pen-fancy';
  if (name.includes('reviewer')) return 'fas fa-check-double';
  if (name === 'assembler') return 'fas fa-puzzle-piece';
  if (name === 'user') return 'fas fa-user';
  return 'fas fa-robot';
}

function getNodeColor(agentName) {
  const name = agentName?.toLowerCase() || '';
  if (name.includes('planner') && !name.includes('reviewer')) return '#7c3aed';
  if (name.includes('reviewer') || name.includes('outline_reviewer')) return '#059669';
  if (name.includes('writer')) return '#2563eb';
  if (name === 'assembler') return '#d97706';
  if (name === 'user') return '#6366f1';
  return '#6b7280';
}

function getNodeStatus(agentMap, agentName) {
  const data = agentMap[agentName];
  if (!data || data.entries.length === 0) return 'pending';
  const lastContent = data.entries[data.entries.length - 1]?.content || '';
  if (typeof lastContent === 'string' && lastContent.toLowerCase().includes('failed')) return 'error';
  return 'done';
}

function getAgentTokenUsage(agentMap, agentName) {
  const data = agentMap[agentName];
  if (!data || data.entries.length === 0) return null;
  let prompt = 0, completion = 0, total = 0;
  data.entries.forEach((entry) => {
    if (entry.token_usage) {
      prompt += entry.token_usage.prompt_tokens || 0;
      completion += entry.token_usage.completion_tokens || 0;
      total += entry.token_usage.total_tokens || 0;
    }
  });
  if (total === 0) return null;
  return { prompt_tokens: prompt, completion_tokens: completion, total_tokens: total };
}

// ============== Main Component ==============

const AgentFlowDiagram = ({ logs, type = 'course', totalTokenUsage }) => {
  const [selectedAgent, setSelectedAgent] = useState(null);

  // Build agent data from logs
  const agentMap = useMemo(() => {
    const map = {};
    (logs || []).forEach((entry) => {
      const name = entry.agent || entry.source || 'unknown';
      if (!map[name]) {
        map[name] = { name, entries: [], stage: entry.stage || 'general' };
      }
      map[name].entries.push(entry);
    });
    return map;
  }, [logs]);

  // Build nodes and edges
  const { initialNodes, initialEdges } = useMemo(() => {
    const nodes = [];
    const edges = [];

    // Determine agents per stage
    const planningAgents = [];
    const writingPairs = []; // [{writer, reviewer}]
    const assemblyAgents = [];

    Object.keys(agentMap).forEach((name) => {
      if (name === 'Expert_Agent') return;
      const stage = agentMap[name].stage;
      if (stage === 'planning') planningAgents.push(name);
      else if (stage === 'writing') {
        // Group writers and reviewers into pairs
        if (name.includes('writer')) {
          const lessonNum = name.match(/L(\d+)|T(\d+)/);
          const num = lessonNum ? (lessonNum[1] || lessonNum[2]) : null;
          const reviewerName = Object.keys(agentMap).find(
            (n) => n.includes('reviewer') && n !== 'outline_reviewer' && n !== 'quiz_planner_reviewer' && n.includes(num ? (name.includes('L') ? `L${num}` : `T${num}`) : '')
          );
          writingPairs.push({ writer: name, reviewer: reviewerName || null, num });
        }
      } else if (stage === 'assembly') assemblyAgents.push(name);
    });

    // Fallback if no data
    if (planningAgents.length === 0) {
      if (type === 'course') {
        planningAgents.push('planner_agent', 'outline_reviewer');
      } else {
        planningAgents.push('quiz_planner', 'quiz_planner_reviewer');
      }
    }
    if (writingPairs.length === 0) {
      writingPairs.push({ writer: type === 'course' ? 'lesson_writer_L1' : 'question_writer_T0', reviewer: type === 'course' ? 'lesson_reviewer_L1' : 'question_reviewer_T0', num: '1' });
    }
    if (assemblyAgents.length === 0) {
      assemblyAgents.push('assembler');
    }

    // Layout constants
    const colX = [80, 380, 700];
    const nodeH = 52;
    const pairH = 130;
    const groupPad = 15;
    const startY = 60;

    // Planning nodes
    planningAgents.forEach((name, i) => {
      nodes.push({
        id: name,
        type: 'agent',
        position: { x: colX[0], y: startY + i * (nodeH + 20) },
        data: {
          label: name.replace(/_/g, ' '),
          icon: getNodeIcon(name),
          color: getNodeColor(name),
          status: getNodeStatus(agentMap, name),
          isSelected: selectedAgent === name,
          onClick: () => setSelectedAgent(selectedAgent === name ? null : name),
          tokenUsage: getAgentTokenUsage(agentMap, name),
        },
      });
    });
    // Intra-planning edges
    for (let i = 0; i < planningAgents.length - 1; i++) {
      edges.push({
        id: `plan-${i}`,
        source: planningAgents[i],
        target: planningAgents[i + 1],
        type: 'smoothstep',
        animated: false,
        style: { stroke: '#c4b5fd', strokeWidth: 1.5, strokeDasharray: '5,4' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#c4b5fd', width: 14, height: 14 },
      });
    }

    // Writing pairs — grouped
    const writingStartY = startY;
    writingPairs.forEach((pair, i) => {
      const groupY = writingStartY + i * pairH;
      const groupId = `group-L${pair.num || i}`;

      // Group background node
      nodes.push({
        id: groupId,
        type: 'group',
        position: { x: colX[1] - groupPad, y: groupY - groupPad },
        data: { label: type === 'course' ? `Lesson ${pair.num || i + 1}` : `Topic ${pair.num || i + 1}`, width: 200, height: pairH - 10 },
        style: { zIndex: -1 },
        selectable: false,
        draggable: true,
      });

      // Writer node
      nodes.push({
        id: pair.writer,
        type: 'agent',
        position: { x: colX[1], y: groupY },
        data: {
          label: pair.writer.replace(/_/g, ' '),
          icon: getNodeIcon(pair.writer),
          color: getNodeColor(pair.writer),
          status: getNodeStatus(agentMap, pair.writer),
          isSelected: selectedAgent === pair.writer,
          onClick: () => setSelectedAgent(selectedAgent === pair.writer ? null : pair.writer),
          tokenUsage: getAgentTokenUsage(agentMap, pair.writer),
        },
      });

      // Reviewer node
      if (pair.reviewer) {
        nodes.push({
          id: pair.reviewer,
          type: 'agent',
          position: { x: colX[1], y: groupY + nodeH + 12 },
          data: {
            label: pair.reviewer.replace(/_/g, ' '),
            icon: getNodeIcon(pair.reviewer),
            color: getNodeColor(pair.reviewer),
            status: getNodeStatus(agentMap, pair.reviewer),
            isSelected: selectedAgent === pair.reviewer,
            onClick: () => setSelectedAgent(selectedAgent === pair.reviewer ? null : pair.reviewer),
            tokenUsage: getAgentTokenUsage(agentMap, pair.reviewer),
          },
        });
        // Writer → Reviewer edge (review loop)
        edges.push({
          id: `wr-${i}`,
          source: pair.writer,
          target: pair.reviewer,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#c4b5fd', strokeWidth: 1.5, strokeDasharray: '5,4' },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#c4b5fd', width: 12, height: 12 },
        });
      }

      // Planning → Writer edge (fan-out from last planning agent)
      const lastPlanner = planningAgents[planningAgents.length - 1];
      edges.push({
        id: `plan-write-${i}`,
        source: lastPlanner,
        target: pair.writer,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#9ca3af', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#6b7280', width: 16, height: 16 },
      });

      // Writer (or reviewer) → Assembler edge (fan-in)
      const sourceForAssembly = pair.reviewer || pair.writer;
      edges.push({
        id: `write-asm-${i}`,
        source: sourceForAssembly,
        target: assemblyAgents[0],
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#9ca3af', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#6b7280', width: 16, height: 16 },
      });
    });

    // Assembly nodes
    const asmY = writingStartY + (writingPairs.length * pairH) / 2 - nodeH / 2;
    assemblyAgents.forEach((name, i) => {
      nodes.push({
        id: name,
        type: 'agent',
        position: { x: colX[2], y: asmY + i * (nodeH + 20) },
        data: {
          label: name.replace(/_/g, ' '),
          icon: getNodeIcon(name),
          color: getNodeColor(name),
          status: getNodeStatus(agentMap, name),
          isSelected: selectedAgent === name,
          onClick: () => setSelectedAgent(selectedAgent === name ? null : name),
          tokenUsage: getAgentTokenUsage(agentMap, name),
        },
      });
    });

    return { initialNodes: nodes, initialEdges: edges };
  }, [agentMap, type, selectedAgent]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edgesState, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes when selection changes
  React.useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges]);

  const selectedData = selectedAgent ? agentMap[selectedAgent] : null;

  return (
    <div style={{ width: '100%' }}>
      {/* React Flow Canvas */}
      <div style={{ width: '100%', height: '500px', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden', backgroundColor: '#fafafa' }}>
        <ReactFlow
          nodes={nodes}
          edges={edgesState}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.3}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#e5e7eb" gap={20} size={1} />
          <Controls position="bottom-right" showInteractive={false} />
          <MiniMap
            nodeColor={(n) => {
              if (n.type === 'group') return '#faf5ff';
              return n.data?.color || '#6b7280';
            }}
            style={{ borderRadius: '8px' }}
          />
        </ReactFlow>
      </div>

      {/* Total Token Usage Summary */}
      {totalTokenUsage && totalTokenUsage.total_tokens > 0 && (
        <div style={{
          marginTop: '0.75rem', padding: '0.7rem 1rem',
          background: 'linear-gradient(135deg, #eff6ff, #f0fdf4)',
          borderRadius: '8px', border: '1px solid #e0e7ff',
          display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center',
        }}>
          <span style={{ fontWeight: '700', fontSize: '0.8rem', color: '#374151' }}>
            <i className="fas fa-coins" style={{ marginRight: '6px', color: '#d97706' }}></i>
            Total Token Usage
          </span>
          <span style={{ fontSize: '0.78rem', color: '#6b7280' }}>
            Prompt: <strong style={{ color: '#2563eb' }}>{totalTokenUsage.prompt_tokens?.toLocaleString()}</strong>
          </span>
          <span style={{ fontSize: '0.78rem', color: '#6b7280' }}>
            Completion: <strong style={{ color: '#059669' }}>{totalTokenUsage.completion_tokens?.toLocaleString()}</strong>
          </span>
          <span style={{ fontSize: '0.85rem', fontWeight: '700', color: '#374151', marginLeft: 'auto' }}>
            Total: {totalTokenUsage.total_tokens?.toLocaleString()} tokens
          </span>
        </div>
      )}

      {/* Legend */}
      <div style={{ marginTop: '0.75rem', padding: '0.6rem 1rem', background: '#f9fafb', borderRadius: '8px', display: 'flex', gap: '1.5rem', flexWrap: 'wrap', fontSize: '0.75rem', color: '#6b7280', alignItems: 'center' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '9px', height: '9px', borderRadius: '50%', backgroundColor: '#10b981' }}></span> Completed
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '9px', height: '9px', borderRadius: '50%', backgroundColor: '#ef4444' }}></span> Error
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '9px', height: '9px', borderRadius: '50%', backgroundColor: '#d1d5db' }}></span> Pending
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <svg width="24" height="10"><path d="M0 5 L24 5" stroke="#9ca3af" strokeWidth="2" fill="none"/><polygon points="20,2 24,5 20,8" fill="#9ca3af"/></svg> Data flow
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <svg width="24" height="10"><path d="M0 5 L24 5" stroke="#c4b5fd" strokeWidth="1.5" strokeDasharray="4,3" fill="none"/></svg> Review loop
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '16px', height: '12px', border: '2px dashed #c4b5fd', borderRadius: '4px', backgroundColor: '#faf5ff' }}></span> Lesson group
        </span>
        <span style={{ marginLeft: 'auto', fontStyle: 'italic' }}>Drag to move nodes. Scroll to zoom. Click a node for details.</span>
      </div>

      {/* Selected Agent Detail Panel */}
      {selectedData && (
        <div style={{
          marginTop: '1rem',
          padding: '1.25rem',
          borderRadius: '12px',
          border: `2px solid ${getNodeColor(selectedAgent)}`,
          backgroundColor: `${getNodeColor(selectedAgent)}08`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '50%',
              backgroundColor: `${getNodeColor(selectedAgent)}15`,
              display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '10px',
            }}>
              <i className={getNodeIcon(selectedAgent)} style={{ color: getNodeColor(selectedAgent), fontSize: '1rem' }}></i>
            </div>
            <div>
              <div style={{ fontWeight: '700', fontSize: '0.95rem' }}>{selectedAgent.replace(/_/g, ' ')}</div>
              <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                <span style={{ background: '#f3f4f6', borderRadius: '4px', padding: '1px 6px', marginRight: '6px' }}>{selectedData.stage}</span>
                {selectedData.entries.length} log entry(s)
                {(() => {
                  const agentTokens = getAgentTokenUsage(agentMap, selectedAgent);
                  if (agentTokens) return (
                    <span style={{ marginLeft: '8px', color: '#d97706' }}>
                      <i className="fas fa-coins" style={{ marginRight: '3px', fontSize: '0.6rem' }}></i>
                      {agentTokens.total_tokens.toLocaleString()} tokens
                      <span style={{ color: '#9ca3af', marginLeft: '4px' }}>
                        (in: {agentTokens.prompt_tokens.toLocaleString()} / out: {agentTokens.completion_tokens.toLocaleString()})
                      </span>
                    </span>
                  );
                  return null;
                })()}
              </div>
            </div>
            <button
              onClick={() => setSelectedAgent(null)}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem', color: '#9ca3af' }}
              aria-label="close"
            >
              &times;
            </button>
          </div>
          <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
            {selectedData.entries.map((entry, idx) => (
              <div key={idx} style={{
                padding: '0.6rem 0.85rem', marginBottom: '0.5rem',
                backgroundColor: 'white', borderRadius: '8px',
                border: '1px solid #e5e7eb', fontSize: '0.82rem',
              }}>
                <pre style={{
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  fontSize: '0.76rem', maxHeight: '180px', overflow: 'auto', lineHeight: '1.5',
                }}>
                  {typeof entry.content === 'object' ? JSON.stringify(entry.content, null, 2) : entry.content}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentFlowDiagram;
