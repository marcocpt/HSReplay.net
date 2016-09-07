import {PlayState} from "./hearthstone";


export interface User {
	id: number;
	username: string;
}

export interface GameReplay {
	shortid: string;
	user: User;
	global_game: GlobalGame;
	spectator_mode: boolean;
	friendly_player_id: number;
	replay_xml: string;
	build: number;
	won: boolean;
	disconnected: boolean;
	reconnecting: boolean;
	visibility: number;
}

export interface GlobalGame {
	build: number;
	match_start: string;
	match_end: string;
	game_type: number;
	ladder_season: number;
	scenario_id: number;
	players: GlobalGamePlayer[];
	num_turns: number;
}

export interface GlobalGamePlayer {
	name:string;
	player_id: number;
	account_hi: number;
	account_lo: number;
	is_ai: boolean;
	is_first: boolean;
	hero_id: string;
	hero_premium: boolean;
	final_state: PlayState;
	wins: number;
	losses: number;
	rank: number;
	legend_rank: number;
}

export const enum Visibility {
	Public = 1,
	Unlisted = 2,
}

export interface ImageProps {
	image: (string) => string;
}

export interface CardArtProps {
	cardArt: (string) => string;
}
