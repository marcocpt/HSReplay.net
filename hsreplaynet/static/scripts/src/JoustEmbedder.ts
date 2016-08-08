import * as Joust from "joust";
import Raven from "raven-js";
import {joustAsset, cardArt} from "./helpers";
import {EventEmitter} from "events";
import MetaDataManager from "./metadata/MetaDataManager";
import LocalStorageBackend from "./metadata/LocalStorageBackend";
import MetricsReporter from "./metrics/MetricsReporter";
import BatchingMiddleware from "./metrics/BatchingMiddleware";
import InfluxMetricsBackend from "./metrics/InfluxMetricsBackend";


export default class JoustEmbedder extends EventEmitter {
	public turn: number = null;
	public reveal: boolean = null;
	public swap: boolean = null;
	public locale: string = "enUS";

	public embed(target: HTMLElement) {
		// find container
		if (!target) {
			throw new Error("No target specified");
		}
		let launcher = Joust.launcher(target);
		let release = Joust.release();

		// setup RavenJS/Sentry
		let logger = null;
		let dsn = JOUST_RAVEN_DSN_PUBLIC;
		if (dsn) {
			let raven = Raven.config(dsn, {
				release: release,
				environment: JOUST_RAVEN_ENVIRONMENT || "development",
			} as any).install(); // until typings are updated for environment
			logger = (err: string|Error) => {
				if (raven) {
					if (typeof err === "string") {
						raven.captureMessage(err);
					}
					else {
						raven.captureException(err);
					}
				}
				let message = err["message"] ? err["message"] : err;
				console.error(message);
			};
			launcher.logger(logger);
		}

		// setup graphics
		launcher.assets((asset: string) => joustAsset(asset));
		launcher.cardArt((cardId: string) => cardArt(cardId));

		// setup metadata
		let metaFlags = {
			has_build: null,
			cached: null,
			fetched: null,
			fallback: null,
		};
		let manager = new MetaDataManager((build: number|"latest", locale: string): string => {
			return HEARTHSTONEJSON_URL.replace(/%\(build\)s/, "" + build).replace(/%\(locale\)s/, locale);
		}, new LocalStorageBackend(), this.locale);
		launcher.metadata((build: number|null, cb: (data: any[]) => void): void => {
			metaFlags.has_build = !!(+build);
			manager.get(+build || "latest", (data: any[]): void => {
				metaFlags.cached = manager.cached;
				metaFlags.fetched = manager.fetched;
				metaFlags.fallback = manager.fallback;
				cb(data);
			});
		});

		// setup influx
		let endpoint = INFLUX_DATABASE_JOUST;
		if (endpoint) {
			let metrics = null;
			let track = (series, values, tags) => {
				if (!tags) {
					tags = {};
				}
				tags["release"] = release;
				tags["locale"] = this.locale;
				switch (series) {
					case "cards_received": // deprecated
					case "metadata":
						let flags = Object.keys(metaFlags);
						for (let i = 0; i < flags.length; i++) {
							let flag = flags[i];
							tags[flag] = metaFlags[flag];
						}
						console.log(tags);
						break;
				}
				metrics.writePoint(series, values, tags);
			};
			metrics = new MetricsReporter(
				new BatchingMiddleware(new InfluxMetricsBackend(endpoint), (): void => {
					metrics.writePoint("watched", {
						percentage: launcher.percentageWatched,
						seconds: launcher.secondsWatched,
						duration: launcher.replayDuration,
					});
				}),
				(series: string): string => "joust_" + series
			);
			launcher.events(track);
		}

		// turn linking
		if (this.turn !== null) {
			launcher.startAtTurn(this.turn);
		}
		launcher.onTurn((newTurn: number) => {
			this.turn = newTurn;
			this.emit("turn", newTurn);
		});

		if (this.reveal !== null) {
			launcher.startRevealed(this.reveal);
		}
		launcher.onToggleReveal((newReveal: boolean) => {
			this.reveal = newReveal;
			this.emit("reveal", newReveal);
		});

		if (this.swap !== null) {
			launcher.startSwapped(this.swap);
		}
		launcher.onToggleSwap((newSwap: boolean) => {
			this.swap = newSwap;
			this.emit("swap", newSwap);
		});

		// initialize joust
		launcher.fromUrl(target.getAttribute("data-replayurl"));
	}
}
