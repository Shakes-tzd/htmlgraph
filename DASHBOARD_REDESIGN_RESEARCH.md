# Dashboard UI Redesign Research - Multi-Agent Focus

**Status:** Research Complete | **Date:** 2026-01-06 | **Next Phase:** Design Review

## Overview

This document summarizes comprehensive research into redesigning the HtmlGraph dashboard to make multi-agent orchestration its visual centerpiece. The research identified critical UX problems and proposes a detailed 5-phase implementation roadmap.

## The Core Problem

**Users cannot easily answer "Who did what work?" despite HtmlGraph having perfect data to show exactly this.**

The current dashboard obscures multi-agent collaboration behind:
- Confusing multi-tab navigation (5 tabs with unclear purposes)
- Table-heavy analytics (5+ tables competing for attention)
- Graph tab wastes space (vis.js visualization shelved but still displayed)
- Agent attribution buried (badges exist but not prominent)
- No timeline view (can't see work continuity across sessions)

## What Changed in This Research

### Problems Documented
1. Graph tab visualization shelved but still taking 15-20% of code
2. Agent attribution not highlighted in multi-agent scenarios
3. Analytics view has 5 tables with no visual insights
4. Multi-agent handoffs completely invisible
5. Sessions view doesn't leverage agent data
6. Visual hierarchy broken (all tabs equal weight)

### Solutions Designed
1. **Remove Graph Tab** - Eliminate vis.js, simplify navigation
2. **Add Agents Tab** - New first-class view for multi-agent metrics
3. **Redesign Analytics** - Timeline focus, collaboration patterns
4. **Enhance Sessions** - Add agent attribution and context
5. **Agent Color System** - Consistent visual identification throughout

## Key Findings

### Current Dashboard Structure
```
Navigation:  [Work] [Graph] [Analytics] [Agents] [Sessions]
             └─ Graph shelved but still visible
             └─ Agents is empty stub
             └─ Work is only decent view

Data Available:
- Feature attribution to agents ✓
- Session agent information ✓
- Event-level agent tracking ✓
- Cost per agent ✓
- Temporal relationships ✓

BUT: UI hides all of this!
```

### Industry Best Practices Researched
- **GitHub Projects:** Kanban with assignee badges, timeline milestones
- **Jira:** Multiple views, assignee metrics, status visualization
- **Linear:** Clean UI, focused information hierarchy
- **DevOps Dashboards:** Visual metrics, multi-agent system monitoring

## Proposed Design

### New Navigation Structure
```
[📊 Work]  [👥 Agents]  [⚡ Analytics]  [💬 Sessions]  [🌙 Theme]

Removed:  Graph tab (vis.js, shelved)
Added:    Agents tab (new multi-agent metrics)
Improved: Work, Analytics, Sessions with agent focus
```

### Agent Color System (WCAG AA Accessible)
```
🔵 claude           #2979FF (Blue)      - Primary reasoning
🟢 codex            #00C853 (Green)     - Exploratory/batch
🟣 orchestrator     #7C4DFF (Purple)    - Coordination
🟡 gemini           #FBC02D (Amber)     - Analysis (FREE)
🟠 gemini-2.0       #FF9100 (Orange)    - Multimodal (FREE)

All use color + icon combinations for accessibility
```

### Four Redesigned Views

#### 1. Work View (Enhanced Kanban)
- Track-grouped kanban with agent badges
- Agent timeline in card details (click to expand)
- Shows which agents worked when
- Start/end dates visible
- Cost and event count displayed

#### 2. Agents View (NEW)
- Workload distribution (horizontal bar chart)
- Cost breakdown by agent (visual bars, not tables)
- Time allocation (hours per agent)
- Skills matrix (agent specializations)
- Recent activity status

#### 3. Analytics View (Redesigned)
- Feature continuity timeline showing agent contributions
- Session-to-session work flow
- Handoff points marked
- Collaboration patterns (handoffs vs parallel)
- Temporal relationships clear

#### 4. Sessions View (Enhanced)
- Agent attribution per session
- Session timeline with agent context
- Handoff chain visualization
- Related sessions linked
- Duration and cost displayed

## Implementation Roadmap (5 Phases)

### Phase 1: Foundation (1-2 Days)
Remove graph tab, prepare for redesign
- Delete vis.js dependency
- Simplify navigation to 4 tabs
- Enhance work card agent display
- **Risk:** Low | **Rollback:** Easy

### Phase 2: Agents Tab (2-3 Days)
Create comprehensive multi-agent metrics view
- Implement agent color system
- Build workload distribution charts
- Create cost visualization
- Add skills matrix and activity status
- **Risk:** Low | **Rollback:** Easy (new tab)

### Phase 3: Analytics Redesign (3-4 Days)
Replace table-heavy view with collaboration focus
- Design timeline component
- Replace 5 tables with 3-4 visual cards
- Implement collaboration metrics
- Add drill-down capability
- **Risk:** Medium | **Rollback:** Keep old code commented

### Phase 4: Sessions Enhancement (1-2 Days)
Add agent attribution to sessions
- Enhance session cards with agent info
- Implement handoff chain visualization
- Build session timeline
- Add related sessions linking
- **Risk:** Low | **Rollback:** Easy

### Phase 5: Polish & Optimization (1-2 Days)
Finalize for production
- Performance testing (1000+ features)
- Accessibility audit (WCAG 2.1 AA)
- Mobile responsiveness
- Edge case handling
- **Risk:** Low | **Rollback:** Easy

**Total Effort:** 8-13 days (target: 2-week sprint)

## Success Metrics

### User Experience
- Dashboard loads in <2s (improved)
- New users understand multi-agent work within 30s
- "Who did what?" answerable without opening details
- Agent metrics found in <1 click

### Performance
- Remove 50KB of vis.js code
- Reduce CSS by 15%
- Page load <2s on 4G network

### Adoption
- Analytics clicked 3x more
- Agents tab used in >80% of sessions
- Agent filtering used in >50% of sessions

## Technical Notes

### No Breaking Changes
- Feature HTML structure unchanged
- Session data format preserved
- Existing kanban functionality maintained
- Theme switching preserved

### New Dependencies
- None! Removing vis.js actually reduces dependencies

### Backward Compatibility
- Old analytics view can be kept as fallback
- Session files don't need updates
- Feature files don't need updates

## Risk Assessment

### High Risk (Mitigated)
**Data accuracy in timeline view**
- Mitigation: Cross-validate with session data
- Testing: Unit tests for timeline calculation
- Rollback: Keep old view accessible

### Medium Risk (Mitigated)
**Performance with large datasets (1000+ features)**
- Mitigation: Lazy loading, pagination
- Testing: Load test with real data
- Optimization: Virtualization for long lists

**Color accessibility for agents**
- Mitigation: Color + icon combinations
- Testing: WebAIM contrast checker
- Fallback: Pattern-based identification

### Low Risk (Standard)
Breaking existing kanban functionality
- Mitigation: Minimal changes to structure
- Testing: Regression tests
- Rollback: Keep old CSS commented

## Deliverables Created

### 1. DASHBOARD_UI_REDESIGN.md (500+ Lines)
Comprehensive design specification including:
- Current state analysis with problems
- Design goals (primary and secondary)
- Visual mockups (ASCII + descriptions)
- Component specifications
- Implementation roadmap (detailed 5 phases)
- Technical architecture
- Risk assessment and mitigation
- Success metrics
- Industry best practices research

### 2. spk-dashboard-redesign.html
HtmlGraph spike document with:
- Executive summary
- Current problems identified
- Design goals
- View mockups
- Implementation roadmap
- Success metrics
- Key deliverables
- Research conducted
- Recommendations

### 3. This Research Document
Summary of findings, approach, and recommendations

## Recommendations

### Immediate Actions (This Week)
1. Review design specification
2. Get stakeholder feedback on agent colors
3. Estimate effort per phase
4. Schedule design review meeting

### Next Phase (Implementation Planning)
1. Create visual mockups (Figma/HTML prototype)
2. Assign implementation tasks
3. Set up feature tracking in .htmlgraph
4. Begin Phase 1 (remove graph tab)

### Launch Strategy
1. Phase 1 + 2: Internal release for team feedback
2. Phase 3: Broader preview
3. Phase 4-5: Final polish and release as v0.4.0

## Why This Design Matters

The current HtmlGraph dashboard is like a beautiful database with no UI. All the data exists—feature timelines, agent attribution, cost tracking—but users can't see it without tedious clicking and table reading.

This redesign makes the **obvious thing obvious**: **Multi-agent collaboration is the core value.**

Every view answers: "Who did what work and when?"
- Work: Agent badges and timeline
- Agents: Metrics and comparison
- Analytics: Collaboration patterns and handoffs
- Sessions: Agent context and relationships

## Conclusion

The research phase is complete. The design specification is detailed, actionable, and de-risked. The 5-phase roadmap is achievable in 2-3 weeks.

Next step: **Approve design and begin Phase 1 implementation.**

---

**Research Date:** 2026-01-06
**Researcher:** Claude Code
**Status:** Ready for Design Review & Approval
**Files:**
- `DASHBOARD_UI_REDESIGN.md` - Full specification
- `spk-dashboard-redesign.html` - HtmlGraph spike
- `DASHBOARD_REDESIGN_RESEARCH.md` - This summary
