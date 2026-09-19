// Authorization policy for RoomieOps BUILD_IT mode
// Users can only access households they are members of

// Read access: user must be a member of the household
permit(
  principal,
  action == Action::"read_household",
  resource
)
when {
  principal in resource
};

// Mutations: user must be a member of the household
permit(
  principal,
  action in [
    Action::"create_expense",
    Action::"create_maintenance",
    Action::"create_shopping_item"
  ],
  resource
)
when {
  principal in resource
};
