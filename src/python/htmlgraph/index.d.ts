/**
 * HtmlGraph TypeScript Type Definitions
 *
 * Python SDK type definitions for TypeScript/JavaScript interoperability
 * when using HtmlGraph via tools like pyodide or similar bridges.
 */

// ============================================================================
// Core Types
// ============================================================================

export interface Step {
    description: string;
    completed: boolean;
    agent?: string;
    timestamp?: string;
}

export interface Edge {
    target_id: string;
    title?: string;
    relationship?: string;
}

export interface Node {
    id: string;
    title: string;
    type: string;
    status: string;
    priority: string;
    created: string;
    updated: string;
    content?: string;
    tags?: string[];
    steps?: Step[];
    edges?: Record<string, Edge[]>;
    track?: string;
    agent_assigned?: string;
}

export interface Feature extends Node {
    type: 'feature';
}

export interface Bug extends Node {
    type: 'bug';
}

export interface Chore extends Node {
    type: 'chore';
    maintenance_type?: 'corrective' | 'adaptive' | 'perfective' | 'preventive';
    technical_debt_score?: number;
}

export interface Spike extends Node {
    type: 'spike';
    spike_type?: 'technical' | 'architectural' | 'risk' | 'general';
    timebox_hours?: number;
    findings?: string;
    decision?: string;
}

export interface Requirement {
    description: string;
    priority: 'must-have' | 'should-have' | 'nice-to-have';
}

export interface AcceptanceCriteria {
    description: string;
    test_case: string;
}

export interface Spec {
    overview: string;
    context?: string;
    requirements: Requirement[];
    acceptance_criteria?: AcceptanceCriteria[];
}

export interface Task {
    description: string;
    estimated_hours?: number;
}

export interface Phase {
    name: string;
    tasks: Task[];
}

export interface Plan {
    phases: Phase[];
    total_estimated_hours?: number;
}

export interface Track {
    id: string;
    title: string;
    description?: string;
    priority: string;
    status: string;
    created: string;
    updated: string;
    spec?: Spec;
    plan?: Plan;
}

// ============================================================================
// Analytics Types
// ============================================================================

export interface Bottleneck {
    id: string;
    title: string;
    status: string;
    priority: string;
    blocks_count: number;
    impact_score: number;
    blocked_tasks: string[];
}

export interface Recommendation {
    id: string;
    title: string;
    priority: string;
    score: number;
    reasons: string[];
    estimated_hours?: number;
    unlocks_count: number;
    unlocks: string[];
}

export interface ParallelWork {
    max_parallelism: number;
    ready_now: number;
    total_ready: number;
    level_count: number;
    next_level: string[][];
}

export interface Risk {
    high_risk_count: number;
    high_risk_tasks: Array<{
        id: string;
        title: string;
        risk_factors: string[];
    }>;
    circular_dependencies: string[][];
    orphaned_count: number;
    recommendations: string[];
}

export interface Impact {
    node_id: string;
    direct_dependents: string[];
    total_impact: number;
    completion_impact: number;
    unlocks_count: number;
    affected_tasks: string[];
}

// ============================================================================
// Collection Interface
// ============================================================================

export interface Collection<T extends Node> {
    /**
     * Get all nodes in the collection
     */
    all(): T[];

    /**
     * Get a single node by ID
     */
    get(id: string): T | null;

    /**
     * Query nodes matching criteria
     */
    where(filters: Partial<T>): T[];

    /**
     * Create a new node (returns builder for features)
     */
    create(title: string): T | FeatureBuilder;

    /**
     * Edit a node with context manager-like behavior
     */
    edit(id: string): EditContext<T>;

    /**
     * Batch update multiple nodes
     */
    batch_update(ids: string[], updates: Partial<T>): void;

    /**
     * Mark nodes as done
     */
    mark_done(ids: string[]): void;

    /**
     * Assign nodes to an agent
     */
    assign(ids: string[], agent: string): void;
}

// ============================================================================
// Builder Interfaces
// ============================================================================

export interface FeatureBuilder {
    set_priority(priority: string): FeatureBuilder;
    set_description(description: string): FeatureBuilder;
    set_track(track_id: string): FeatureBuilder;
    add_steps(steps: string[]): FeatureBuilder;
    add_tags(tags: string[]): FeatureBuilder;
    blocked_by(feature_ids: string[]): FeatureBuilder;
    save(): Feature;
}

export interface TrackBuilder {
    title(title: string): TrackBuilder;
    description(description: string): TrackBuilder;
    priority(priority: string): TrackBuilder;
    with_spec(spec: {
        overview: string;
        context?: string;
        requirements: Array<[string, string] | string>;
        acceptance_criteria?: Array<[string, string] | string>;
    }): TrackBuilder;
    with_plan_phases(phases: Array<[string, string[]]>): TrackBuilder;
    create(): Track;
}

export interface EditContext<T> {
    __enter__(): T;
    __exit__(): void;
}

// ============================================================================
// SDK Interface
// ============================================================================

export interface SDK {
    agent: string;

    // Collections
    features: Collection<Feature>;
    bugs: Collection<Bug>;
    chores: Collection<Chore>;
    spikes: Collection<Spike>;
    epics: Collection<Node>;
    phases: Collection<Node>;
    tracks: {
        all(): Track[];
        get(id: string): Track | null;
        builder(): TrackBuilder;
    };

    // Analytics
    find_bottlenecks(options?: { top_n?: number }): Bottleneck[];
    recommend_next_work(options?: { agent_count?: number }): Recommendation[];
    get_parallel_work(options?: { max_agents?: number }): ParallelWork;
    assess_risks(): Risk;
    analyze_impact(node_id: string): Impact;
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a new SDK instance
 */
export function SDK(options?: { agent?: string }): SDK;

/**
 * Create a new HtmlGraph instance
 */
export function HtmlGraph(directory: string): any;

// ============================================================================
// Exports
// ============================================================================

export default SDK;
