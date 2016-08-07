// various global module definitions
// this file should be picked up automatically by the typescript compiler

declare var STATIC_URL: string;
declare var HEARTHSTONE_ART_URL: string;
declare var JOUST_STATIC_URL: string;
declare var JOUST_RAVEN_DSN_PUBLIC: string;
declare var JOUST_RAVEN_ENVIRONMENT: string;
declare var HEARTHSTONEJSON_URL: string;
declare var INFLUX_DATABASE_JOUST: string;

declare module "clipboard" {
	export default class Clipboard {
		constructor(selector: any, options?: any);

		destroy(): void;

		on(event: string, func: any): any;
	}
}

declare module "joust" {
	export class Launcher {
		width(width: number): Launcher;

		height(height: number): Launcher;

		assets(assets: string|((asset: string) => string)): Launcher;

		cardArt(url: string|((cardId: string) => string)): Launcher;

		metadata(query: (build: number|null, cb: (cards: any[]) => void) => void): Launcher;

		setOptions(opts: any): Launcher;

		onTurn(callback: (turn: number) => void): Launcher;

		onToggleReveal(callback: (reveal: boolean) => void): Launcher;

		onToggleSwap(callback: (swap: boolean) => void): Launcher;

		startPaused(paused?: boolean): Launcher;

		startAtTurn(turn: number): Launcher;

		startRevealed(reveal: boolean): Launcher;

		startSwapped(swap: boolean): Launcher;

		logger(logger: (message: string | Error) => void): Launcher;

		events(cb: (event: string, values: Object, tags?: Object) => void): Launcher;

		debug(enable?: boolean): Launcher;

		fromUrl(url: string): void;

		percentageWatched: number;

		secondsWatched: number;

		replayDuration: number;
	}

	export function release(): string;

	export function launcher(target: string | HTMLElement): Launcher;
}
