class ChecklistNotFoundError(Exception):
    pass


class ChecklistItemNotFoundError(Exception):
    pass


class ChecklistHasPendingTasksError(Exception):
    pass
