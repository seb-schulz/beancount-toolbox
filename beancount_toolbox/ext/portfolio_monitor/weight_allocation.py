"""
Portfolio weight allocation algorithm.

This module handles hierarchical weight distribution for portfolio accounts,
respecting custom weight directives while ensuring weights sum to 1.0 at each level.
"""
import typing
from decimal import Decimal
from fava.core import tree


def is_ancestor(ancestor: str, descendant: str) -> bool:
    """Check if ancestor is ancestor of descendant in account hierarchy.

    Args:
        ancestor: The potential ancestor account name
        descendant: The potential descendant account name

    Returns:
        True if ancestor is an ancestor of descendant (or equal), False otherwise

    Examples:
        >>> is_ancestor("Assets", "Assets:Checking")
        True
        >>> is_ancestor("Assets:Checking", "Assets:Checking")
        True
        >>> is_ancestor("Assets:Checking", "Liabilities:Loan")
        False
    """
    return ancestor == descendant or descendant.startswith(ancestor + ":")


def preprocess_weights(
    root_node: tree.TreeNode,
    weight_entries: typing.Dict[str, typing.Dict[str, Decimal]]
) -> typing.Tuple[typing.Dict[str, tree.TreeNode], typing.Set[str]]:
    """Build account map and validate all weight constraints.

    Args:
        root_node: Root of the account tree
        weight_entries: Custom weights organized as bucket -> {account: weight}

    Returns:
        Tuple of (account_map, errors) where:
        - account_map: Dict mapping account name to TreeNode
        - errors: Set of validation error messages
    """
    account_map: typing.Dict[str, tree.TreeNode] = {}
    errors: typing.Set[str] = set()

    # Step 1: Build account lookup map
    def build_map(node: tree.TreeNode) -> None:
        account_map[node.name] = node
        for child in node.children:
            build_map(child)

    build_map(root_node)

    # Step 2: Validate each weight entry
    for bucket, weights in weight_entries.items():
        # Validate bucket exists
        if bucket not in account_map:
            errors.add(f"Bucket account '{bucket}' not found in tree")
            continue

        total_weight = Decimal(0)

        for account, weight in weights.items():
            # Validate account exists
            if account not in account_map:
                errors.add(f"Account '{account}' not found in tree")
                continue

            # Validate weight range
            if weight < 0 or weight > 1:
                errors.add(
                    f"Weight {weight} for '{account}' must be in [0, 1]"
                )
                continue

            # Validate bucket is ancestor of account
            if not is_ancestor(bucket, account):
                errors.add(
                    f"Bucket '{bucket}' is not ancestor of '{account}'"
                )
                continue

            total_weight += weight

        # Validate total weight doesn't exceed 1.0
        if total_weight > 1:
            errors.add(
                f"Total custom weights in bucket '{bucket}' "
                f"exceed 1.0: {total_weight}"
            )

    return account_map, errors


def compute_weights(
    node: tree.TreeNode,
    weight_entries: typing.Dict[str, typing.Dict[str, Decimal]],
    account_map: typing.Dict[str, tree.TreeNode],
    allocated_weight: Decimal,
    result: typing.Dict[str, Decimal],
    target_weights: typing.Dict[str, Decimal] | None = None
) -> None:
    """Recursively compute and assign weights to all descendant accounts.

    Args:
        node: Current tree node being processed
        weight_entries: Custom weight specifications (bucket -> {account: weight})
        account_map: Account name to TreeNode lookup
        allocated_weight: Weight allocated to this node from parent
        result: Output dictionary (modified in place)
        target_weights: Specific weights that must be achieved for certain accounts
                       (propagated from ancestor buckets)

    Raises:
        ValueError: If weights at this level don't sum correctly
    """
    if target_weights is None:
        target_weights = {}

    # Base case: Leaf node - record weight and return
    if not node.children:
        result[node.name] = allocated_weight
        return

    # Recursive case: Distribute weight among children

    # Step 1: Collect all target weights from current bucket and propagate from above
    child_target_weights: typing.Dict[str, typing.Dict[str, Decimal]] = {}
    child_local_weights: typing.Dict[str, Decimal] = {}  # Direct children with local weights

    # Add LOCAL weights from current node acting as a bucket (these are relative to allocated_weight)
    if node.name in weight_entries:
        for account, custom_weight in weight_entries[node.name].items():
            # Check if this is a direct child (local weight) or descendant (target weight)
            is_direct_child = False
            for child in node.children:
                if child.name == account:
                    # Direct child - this is a local relative weight
                    child_local_weights[child.name] = custom_weight
                    is_direct_child = True
                    break

            if not is_direct_child:
                # Not a direct child - it's a target weight for a descendant
                for child in node.children:
                    if is_ancestor(child.name, account):
                        if child.name not in child_target_weights:
                            child_target_weights[child.name] = {}
                        child_target_weights[child.name][account] = custom_weight * allocated_weight
                        break

    # Propagate target weights from ancestors (but don't override local weights)
    for target_account, target_weight in target_weights.items():
        if not is_ancestor(node.name, target_account):
            continue

        # Check if this target has a local weight defined - if so, local takes precedence
        has_local_weight = False
        if node.name in weight_entries and target_account in weight_entries[node.name]:
            has_local_weight = True

        if not has_local_weight:
            for child in node.children:
                if is_ancestor(child.name, target_account):
                    if child.name not in child_target_weights:
                        child_target_weights[child.name] = {}
                    # Only propagate if not overridden locally
                    if target_account not in child_local_weights.values():
                        child_target_weights[child.name][target_account] = target_weight
                    break

    # Step 2: Calculate weights for direct children
    children_weights: typing.Dict[str, Decimal] = {}

    # Priority 1: Use local weights (relative to allocated_weight)
    for child_name, local_weight in child_local_weights.items():
        children_weights[child_name] = local_weight * allocated_weight

    # Priority 2: For children without local weights but with target weights, sum them up
    for child in node.children:
        if child.name not in children_weights and child.name in child_target_weights:
            children_weights[child.name] = sum(child_target_weights[child.name].values(), start=Decimal(0))

    # Step 3: Calculate remaining weight after custom allocations
    remaining_weight = allocated_weight
    unweighted_children: typing.List[tree.TreeNode] = []

    for child in node.children:
        if child.name in children_weights:
            remaining_weight -= children_weights[child.name]
        else:
            unweighted_children.append(child)

    # Step 4: Distribute remaining weight
    if unweighted_children:
        # Distribute remaining weight equally among unweighted children
        equal_share = remaining_weight / Decimal(len(unweighted_children))
        for child in unweighted_children:
            children_weights[child.name] = equal_share
    elif remaining_weight > Decimal("0.0001"):  # Allow small floating point errors
        # All children have custom weights but they don't sum to 1.0
        # This is an error - weights must sum to allocated_weight
        raise ValueError(
            f"All children of '{node.name}' have explicit weights but they "
            f"sum to {allocated_weight - remaining_weight}, leaving "
            f"{remaining_weight} unallocated. Please add explicit weights for "
            f"all siblings or ensure they sum to {allocated_weight}."
        )

    # Step 5: Validate total weights sum correctly
    total_allocated = sum(children_weights.values())
    # Allow small floating point errors (0.01%)
    if abs(total_allocated - allocated_weight) > Decimal("0.0001"):
        raise ValueError(
            f"Weights for children of '{node.name}' sum to {total_allocated}, "
            f"expected {allocated_weight}"
        )

    # Step 6: Recursively process all children
    for child in node.children:
        child_weight = children_weights.get(child.name, Decimal(0))
        child_targets = child_target_weights.get(child.name, {})
        compute_weights(
            child,
            weight_entries,
            account_map,
            child_weight,
            result,
            child_targets
        )


def weight_list(
    root_node: tree.TreeNode,
    weight_entries: typing.Dict[str, typing.Dict[str, Decimal]],
    root_weight: Decimal = Decimal(1)
) -> typing.Dict[str, Decimal]:
    """Compute hierarchical weight allocation for account tree.

    This function implements a two-pass algorithm:
    1. Validation pass: Build account map and validate all constraints
    2. Computation pass: Recursively compute weights top-down

    Args:
        root_node: Root of the account tree
        weight_entries: Custom weights organized as bucket -> {account: weight}
                       Example: {"Assets:US": {"Assets:US:ETrade:ITOT": Decimal("0.2")}}
        root_weight: Initial weight for root (default 1.0)

    Returns:
        Dict mapping account names to absolute weights (leaf accounts only)

    Raises:
        ValueError: If validation fails (invalid weights, missing accounts, etc.)

    Examples:
        >>> # Tree with 3 children, one with custom weight
        >>> weight_list(root, {"Assets:US": {"Assets:US:ITOT": Decimal("0.2")}})
        {
            "Assets:US:ITOT": Decimal("0.2"),
            "Assets:US:VBMPX": Decimal("0.4"),
            "Assets:US:VTI": Decimal("0.4")
        }
    """
    # Pass 1: Validate and preprocess
    account_map, errors = preprocess_weights(root_node, weight_entries)

    if errors:
        error_msg = "\n".join(sorted(errors))
        raise ValueError(f"Weight validation errors:\n{error_msg}")

    # Pass 2: Compute weights recursively
    result: typing.Dict[str, Decimal] = {}
    compute_weights(root_node, weight_entries, account_map, root_weight, result)

    return result
