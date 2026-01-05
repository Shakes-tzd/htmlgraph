from __future__ import annotations

from collections.abc import Iterable

from htmlgraph.cli_framework import BaseCommand, CommandError, CommandResult


class FeatureCreateCommand(BaseCommand):
    def __init__(
        self,
        *,
        collection: str,
        title: str,
        description: str,
        priority: str,
        steps: Iterable[str] | None,
    ) -> None:
        super().__init__()
        self.collection = collection
        self.title = title
        self.description = description
        self.priority = priority
        self.steps = list(steps) if steps else []

    def execute(self) -> CommandResult:
        sdk = self.get_sdk()

        if self.collection == "features":
            builder = sdk.features.create(
                title=self.title,
                description=self.description,
                priority=self.priority,
            )
            if self.steps:
                builder.add_steps(self.steps)
            node = builder.save()
        else:
            node = sdk.session_manager.create_feature(
                title=self.title,
                collection=self.collection,
                description=self.description,
                priority=self.priority,
                steps=self.steps,
                agent=self.agent,
            )

        text = [
            f"Created: {node.id}",
            f"  Title: {node.title}",
            f"  Status: {node.status}",
            f"  Path: {self.graph_dir}/{self.collection}/{node.id}.html",
        ]
        return CommandResult(data=node, text=text)


class FeatureStartCommand(BaseCommand):
    def __init__(self, *, collection: str, feature_id: str) -> None:
        super().__init__()
        self.collection = collection
        self.feature_id = feature_id

    def execute(self) -> CommandResult:
        sdk = self.get_sdk()
        collection = getattr(sdk, self.collection, None)

        if not collection:
            raise CommandError(f"Collection '{self.collection}' not found in SDK.")

        node = collection.start(self.feature_id)
        if node is None:
            raise CommandError(
                f"Feature '{self.feature_id}' not found in {self.collection}."
            )

        status = sdk.session_manager.get_status()
        text = [
            f"Started: {node.id}",
            f"  Title: {node.title}",
            f"  Status: {node.status}",
            f"  WIP: {status['wip_count']}/{status['wip_limit']}",
        ]
        return CommandResult(data=node, text=text)


class FeatureCompleteCommand(BaseCommand):
    def __init__(self, *, collection: str, feature_id: str) -> None:
        super().__init__()
        self.collection = collection
        self.feature_id = feature_id

    def execute(self) -> CommandResult:
        sdk = self.get_sdk()
        collection = getattr(sdk, self.collection, None)

        if not collection:
            raise CommandError(f"Collection '{self.collection}' not found in SDK.")

        node = collection.complete(self.feature_id)
        if node is None:
            raise CommandError(
                f"Feature '{self.feature_id}' not found in {self.collection}."
            )

        text = [
            f"Completed: {node.id}",
            f"  Title: {node.title}",
        ]
        return CommandResult(data=node, text=text)
