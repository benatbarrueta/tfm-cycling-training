import { useEffect, useState } from "react";
import type {
  ActivityInput,
} from "../types/training";
import type {
  ActivityRecord,
} from "../types/calendar";

const STORAGE_KEY = "cycling-training-activities";

function loadActivities(): ActivityRecord[] {
  const savedActivities =
    localStorage.getItem(STORAGE_KEY);

  if (savedActivities === null) {
    return [];
  }

  try {
    const parsedActivities: unknown =
      JSON.parse(savedActivities);

    if (!Array.isArray(parsedActivities)) {
      return [];
    }

    return parsedActivities as ActivityRecord[];
  } catch {
    return [];
  }
}

export function useActivities() {
  const [activities, setActivities] = useState<
    ActivityRecord[]
  >(loadActivities);

  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
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