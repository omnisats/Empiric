import { useContract, useStarknetCall } from "@starknet-react/core";
import { strToHexFelt } from "../../utils/felt";
import { getOracleAddress } from "../services/address.service";
import { networkId } from "../services/wallet.service";
import OracleAbi from "../abi/Oracle.json";
import { Abi } from "starknet";
import { bigNumberishArrayToDecimalStringArray } from "starknet/utils/number";

export const AssetKeys = [
  "eth/usd",
  "btc/usd",
  "luna/usd",
  "sol/usd",
  "avax/usd",
  "doge/usd",
  "shib/usd",
  "temp/usd",
  "eth/mxn",
];

export type AssetKeyT = typeof AssetKeys[number];

export const useOracleContract = () => {
  const network = networkId();
  const oracleContractAddress = getOracleAddress(network);
  return useContract({
    abi: OracleAbi as Abi,
    address: oracleContractAddress,
  });
};

interface GetDecimalsHookT {
  decimals: number;
  loading: boolean;
  error: string;
}

const useOracleGetDecimals = (assetKey: AssetKeyT): GetDecimalsHookT => {
  const { contract } = useOracleContract();
  const { data, loading, error } = useStarknetCall({
    contract,
    method: "get_decimals",
    args: [],
  });
  let decimals: number | undefined = undefined;
  if (data !== undefined) {
    decimals = parseInt(bigNumberishArrayToDecimalStringArray(data)[0]);
  }
  return { decimals, loading, error };
};

export type OracleResponseT = {
  value: number;
  lastUpdatedTimestamp: number;
};

export interface GetValueHookT {
  oracleResponse: OracleResponseT | undefined;
  loading: boolean;
  error: string;
}

export const useOracleGetValue = (assetKey: AssetKeyT): GetValueHookT => {
  const { contract } = useOracleContract();
  const { decimals } = useOracleGetDecimals(assetKey);
  const arg = strToHexFelt(assetKey);
  const { data, loading, error } = useStarknetCall({
    contract,
    method: "get_value",
    args: [arg],
  });

  if (error !== undefined) {
    console.error(
      `Error retrieving price for ${assetKey}, encoded as ${arg}`,
      error
    );
  }

  let oracleResponse: OracleResponseT | undefined = undefined;
  if (data !== undefined) {
    const [strValue, strLastUpdatedTimestamp] =
      bigNumberishArrayToDecimalStringArray(data);
    const value = parseInt(strValue) / 10 ** decimals;
    const lastUpdatedTimestamp = parseInt(strLastUpdatedTimestamp);
    oracleResponse = {
      value: isNaN(value) ? undefined : value,
      lastUpdatedTimestamp: isNaN(lastUpdatedTimestamp)
        ? undefined
        : lastUpdatedTimestamp,
    };
  }
  return { oracleResponse, loading, error };
};