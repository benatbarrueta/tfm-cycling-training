import { useEffect, useState } from "react";
import type {
  ActivityInput,
} from "../types/training";
import type {
  ActivityRecord,
} from "../types/calendar";
import { readMigratedStorage, storageKeys } from "../config/storage";

function loadActivities(): ActivityRecord[] {
  return readMigratedStorage("activities", (value) =>
    Array.isArray(value) ? (value as ActivityRecord[]) : null,
  ) ?? [];
}

export function useActivities() {
  const [activities, setActivities] = useState<
    ActivityRecord[]
  >(loadActivities);

  useEffect(() => {
    localStorage.setItem(
      storageKeys.activities,
      JSON.stringify(activities),
    );
  }, [activities]);

  function addActivity(
    activity: ActivityInput,
  ): ActivityRecord {
    const record: ActivityRecord = {
      ...activity,
      id: crypto.randomUUID(),
    };

    setActivities((currentActivities) =>
      [record, ...currentActivities].sort(
        (first, second) =>
          second.date.localeCompare(first.date),
      ),
    );

    return record;
  }

  function removeActivity(activityId: string) {
    setActivities((currentActivities) =>
      currentActivities.filter(
        (activity) =>
          activity.id !== activityId,
      ),
    );
  }

  return {
    activities,
    addActivity,
    removeActivity,
  };
}