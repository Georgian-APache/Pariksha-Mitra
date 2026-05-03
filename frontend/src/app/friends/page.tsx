"use client";

import { useState, useEffect, useCallback } from "react";
import { Users, Trophy, Flame, BookOpen, Copy, Check, UserPlus, Loader2, Crown } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import { loadKeys } from "@/lib/byok";
import type { FriendStats, FriendsLeaderboard } from "@/lib/types";

export default function FriendsPage() {
  const userId = loadKeys().userId;
  const [data, setData] = useState<FriendsLeaderboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [addId, setAddId] = useState("");
  const [adding, setAdding] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await api<FriendsLeaderboard>(`/friends/${userId}`);
      setData(res);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { load(); }, [load]);

  async function addFriend() {
    if (!userId || !addId.trim()) return;
    setAdding(true);
    try {
      const res = await api<{ status: string; friend_name: string }>("/friends/add", {
        method: "POST",
        body: { user_id: userId, friend_id: addId.trim() },
      });
      toast.success(
        res.status === "already_friends"
          ? `Already friends with ${res.friend_name}`
          : `Added ${res.friend_name} as a friend!`
      );
      setAddId("");
      await load();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setAdding(false);
    }
  }

  function copyId() {
    if (!userId) return;
    navigator.clipboard.writeText(userId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!userId) {
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-4">
        <Users className="size-10 mx-auto text-muted-foreground" />
        <h2 className="text-xl font-semibold">Complete onboarding first</h2>
        <p className="text-sm text-muted-foreground">You need a profile to use the friends leaderboard.</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
          <Trophy className="size-6 text-amber-500" /> Friends Leaderboard
        </h1>
        <p className="text-sm text-muted-foreground">
          Healthy competition — see who&apos;s most ready for the exam.
        </p>
      </div>

      {/* Add friend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <UserPlus className="size-4" /> Add a friend
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              placeholder="Paste your friend's User ID"
              value={addId}
              onChange={(e) => setAddId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addFriend()}
            />
            <Button onClick={addFriend} disabled={adding || !addId.trim()}>
              {adding ? <Loader2 className="size-4 animate-spin" /> : "Add"}
            </Button>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
            <span className="flex-1 font-mono truncate">Your ID: {userId}</span>
            <button
              type="button"
              onClick={copyId}
              className="shrink-0 hover:text-foreground transition"
            >
              {copied ? <Check className="size-3.5 text-green-500" /> : <Copy className="size-3.5" />}
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Share your ID with friends so they can add you. IDs are found on this page.
          </p>
        </CardContent>
      </Card>

      {/* Leaderboard */}
      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground py-8 justify-center">
          <Loader2 className="size-4 animate-spin" /> Loading leaderboard…
        </div>
      ) : !data || data.leaderboard.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground space-y-2">
            <Users className="size-8 mx-auto opacity-40" />
            <p>No friends yet. Share your ID and start competing!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {data.leaderboard.map((friend, idx) => (
            <FriendCard key={friend.user_id} friend={friend} rank={idx + 1} myId={data.my_id} />
          ))}
        </div>
      )}
    </div>
  );
}

function FriendCard({ friend, rank, myId }: { friend: FriendStats; rank: number; myId: string }) {
  const isMe = friend.user_id === myId;
  const readinessPct = Math.round(friend.readiness * 100);
  const coveragePct = Math.round(friend.coverage * 100);
  const masteryPct = Math.round(friend.mastery_avg * 100);

  return (
    <div
      className={`rounded-xl border p-4 space-y-3 transition ${
        isMe
          ? "border-primary/50 bg-primary/5"
          : "border-border bg-card hover:border-border/80"
      }`}
    >
      {/* Header row */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <div className={`size-10 rounded-full flex items-center justify-center text-sm font-bold ${
            rank === 1 ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400" :
            rank === 2 ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" :
            rank === 3 ? "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400" :
            "bg-muted text-muted-foreground"
          }`}>
            {friend.display_name.slice(0, 2).toUpperCase()}
          </div>
          {rank === 1 && (
            <Crown className="size-3.5 text-amber-500 absolute -top-1.5 -right-1 rotate-12" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold truncate">{friend.display_name}</span>
            {isMe && <Badge variant="outline" className="text-[10px] px-1.5 py-0">You</Badge>}
            <span className="text-xs text-muted-foreground ml-auto">#{rank}</span>
          </div>
          <div className="text-xs text-muted-foreground">
            {friend.target_exam} · {friend.daily_hours}h/day
            {friend.exam_date && ` · exam ${friend.exam_date}`}
          </div>
        </div>
      </div>

      {/* Readiness bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Exam readiness</span>
          <span className="font-semibold tabular-nums">{readinessPct}%</span>
        </div>
        <div className="h-2 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              readinessPct >= 70 ? "bg-green-500" :
              readinessPct >= 40 ? "bg-amber-500" : "bg-red-400"
            }`}
            style={{ width: `${readinessPct}%` }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded-lg bg-muted/50 px-2 py-1.5 space-y-0.5">
          <div className="font-semibold tabular-nums">{coveragePct}%</div>
          <div className="text-muted-foreground flex items-center justify-center gap-1">
            <BookOpen className="size-3" /> Coverage
          </div>
        </div>
        <div className="rounded-lg bg-muted/50 px-2 py-1.5 space-y-0.5">
          <div className="font-semibold tabular-nums">{masteryPct}%</div>
          <div className="text-muted-foreground">Mastery</div>
        </div>
        <div className="rounded-lg bg-muted/50 px-2 py-1.5 space-y-0.5">
          <div className="font-semibold tabular-nums flex items-center justify-center gap-1">
            <Flame className="size-3 text-orange-500" />{friend.streak_days}d
          </div>
          <div className="text-muted-foreground">Streak</div>
        </div>
      </div>

      {/* Top subjects */}
      {friend.top_subjects.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {friend.top_subjects.map(({ subject, score }) => (
            <span
              key={subject}
              className="inline-flex items-center gap-1 text-[11px] rounded-full border border-border px-2 py-0.5 text-muted-foreground"
            >
              {subject.replace(/_/g, " ")} <span className="text-foreground font-medium">{Math.round(score * 100)}%</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
