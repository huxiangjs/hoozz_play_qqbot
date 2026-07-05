#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from fastmcp import Client
import threading
import queue
import json
import argparse

parser = argparse.ArgumentParser(description='Hoozz Play QQ Bot')
parser.add_argument('--url', type=str, required=False, help='MCP URL')
args = parser.parse_args()

mcp_url = args.url if args.url else 'http://localhost:8000/mcp'

class std_io(threading.Thread):
    '''Standard input and output'''

    def __init__(self):
        super().__init__()
        self._queue = queue.Queue(maxsize=0)

    def run(self):
        print('thread running')
        try:
            self._queue.get(block=True)
        except Exception:
            pass
        print('thread exited')

    def stop(self):
        self._queue.put(None)
        self.join()

    def get(self):
        data = None
        try:
            data = input()
        except Exception:
            pass
        return data

    def put(self, data):
        print(data)

class mcp_client:
    '''MCP client'''

    def __init__(self, inout, mcp_url):
        self._inout = inout
        self._client = Client(mcp_url)

    async def _init(self):
        await asyncio.to_thread(self._inout.init)
        print('inout exited')

    async def _get(self):
        result = await asyncio.to_thread(self._inout.get)
        # print(result)
        return result

    async def _put(self, data):
        await asyncio.to_thread(self._inout.put, data)

    async def run(self):
        async with self._client:
            tools = await self._client.list_tools()
            print('All tools:')
            for t in tools:
                print(f'  {t.name}')

        dev_bind = {
            'simple_ctrl_button_led': [
                ['ON', self._dev_button_led_on],
                ['OFF', self._dev_button_led_off],
            ],
            'simple_ctrl_voice_led': [
                ['ON', self._dev_voice_led_on],
                ['OFF', self._dev_voice_led_off],
            ],
            'simple_ctrl_sensor': [
                ['__dynamic_init__', self._dev_sensor_get_value]
            ],
            'simple_ctrl_smart_ir': [
                ['__dynamic_init__', self._dev_smart_ir_get_key_list],
                ['__dynamic_op__', self._dev_smart_ir_press_key]
            ],
        }

        dev_list = [ ]

        while True:
            data = await self._get()
            args = data.split('.')
            top_sel = -1
            result = 'Unkown'
            try:
                top_sel = int(args[0])
            except:
                pass
            if top_sel >= 0 and top_sel < len(dev_list):
                dev_sel = dev_list[top_sel]
                dev_id = dev_sel[0]
                dev_args = dev_sel[3]
                try:
                    class_sel = dev_bind[dev_sel[2]]
                    sub_sel = int(args[1])
                    dynamic_init = None
                    dynamic_exe = None
                    for item in class_sel:
                        if item[0] == '__dynamic_init__':
                            dynamic_init = item[1]
                        elif item[0] == '__dynamic_op__':
                            dynamic_exe = item[1]
                    if dynamic_exe:
                        result = await dynamic_exe(dev_id, sub_sel, dev_args)
                    elif dynamic_init:
                        pass
                    else:
                        func = class_sel[sub_sel][1]
                        result = await func(dev_id, dev_args)
                except:
                    pass
            elif top_sel == -1:
                dev_list = await self._manager_list_available_dev()
                dev_list_str = ''
                for top_i, top in enumerate(dev_list):
                    # Top menu
                    dev_list_str += f'[{top_i}]: {top[1]}\n'
                    # Sub menu
                    if top[2] in dev_bind:
                        sub_menu = dev_bind[top[2]]
                        sub_menu_str = ''
                        dev_id = top[0]
                        dev_args = [ ]
                        for sub_i, sub in enumerate(sub_menu):
                            name = sub[0]
                            if name == '__dynamic_init__':
                                func = sub[1]
                                sub_menu_str += await func(dev_id, dev_args)
                            elif name == '__dynamic_op__':
                                pass
                            else:
                                sub_menu_str += f'  [{sub_i}]: {name}\n'
                        top[3] = dev_args
                        dev_list_str += sub_menu_str
                if len(dev_list_str):
                    dev_list_str = dev_list_str[:-1]
                result = dev_list_str
            await self._put(result)

    async def _manager_list_available_dev(self):
        '''List all available devices'''
        dev_list = [ ]
        async with self._client:
            try:
                result = await self._client.call_tool('manager_list_available_dev', { })
                # print(result)
                for item in result.content:
                    dev_info = json.loads(item.text)
                    device_id = dev_info['device_id']
                    device_name = dev_info['device_name']
                    class_name = dev_info['class_name']
                    dev_list.append([device_id, device_name, class_name, [ ]])
            except:
                pass
        return dev_list

    async def _dev_button_led_on(self, device_id, args):
        '''Turn on the LED'''
        retval = 'Unkown'
        async with self._client:
            try:
                result = await self._client.call_tool(
                    'dev_button_led_set_color',
                    {'device_id': device_id, 'red': 255, 'green': 255, 'blue': 255}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

    async def _dev_button_led_off(self, device_id, args):
        '''Turn off the LED'''
        retval = 'Unkown'
        async with self._client:
            try:
                result = await self._client.call_tool(
                    'dev_button_led_set_color',
                    {'device_id': device_id, 'red': 0, 'green': 0, 'blue': 0}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

    async def _dev_voice_led_on(self, device_id, args):
        '''Turn on the LED'''
        retval = 'Unkown'
        async with self._client:
            try:
                result = await self._client.call_tool(
                    'dev_button_led_set_color',
                    {'device_id': device_id, 'red': 255, 'green': 255, 'blue': 255}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

    async def _dev_voice_led_off(self, device_id, args):
        '''Turn off the LED'''
        retval = 'Unkown'
        async with self._client:
            try:
                result = await self._client.call_tool(
                    'dev_button_led_set_color',
                    {'device_id': device_id, 'red': 0, 'green': 0, 'blue': 0}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

    async def _dev_sensor_get_value(self, device_id, args):
        '''Get sensor data'''
        retval = ''
        async with self._client:
            try:
                result = await self._client.call_tool('dev_sensor_get_sensor_info', {'device_id': device_id})
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                sensor_info = ret_dict['sensor_info']
                query_list = [ ]
                for item in sensor_info:
                    sensor_name = item['sensor_name']
                    sensor_id = item['sensor_id']
                    sensor_type = item['sensor_type']
                    query_list.append({
                        'sensor_id': sensor_id,
                        'sensor_type': sensor_type
                    })
                result = await self._client.call_tool(
                    'dev_sensor_get_sensor_data',
                    {'device_id': device_id, 'query_list': query_list}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                data = ret_dict['data']
                data_dict = { }
                for item in data:
                    sensor_id = item['sensor_id']
                    sensor_type = item['sensor_type']
                    sensor_data = item['sensor_data']
                    if sensor_type not in data_dict:
                        data_dict[sensor_type] = { }
                    data_dict[sensor_type][sensor_id] = sensor_data
                for item in sensor_info:
                    sensor_name = item['sensor_name']
                    sensor_id = item['sensor_id']
                    sensor_type = item['sensor_type']
                    sensor_data = data_dict[sensor_type][sensor_id]
                    retval += f"  {sensor_name}{sensor_id}: {sensor_data}\n"
            except:
                pass
        return retval

    async def _dev_smart_ir_get_key_list(self, device_id, args):
        '''Get IR key list'''
        retval = ''
        async with self._client:
            try:
                result = await self._client.call_tool('dev_smart_ir_get_key_list', {'device_id': device_id})
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                # print(ret_dict)
                key_list = ret_dict['key_list']
                for index, value in enumerate(key_list):
                    retval += f"  [{index}]: {value}\n"
                    args.append(value)
            except:
                pass
        return retval

    async def _dev_smart_ir_press_key(self, device_id, key_index, args):
        '''Press IR key'''
        retval = 'Unkown'
        async with self._client:
            try:
                key_name = args[key_index]
                result = await self._client.call_tool(
                    'dev_smart_ir_press_key',
                    {'device_id': device_id, 'key_name': key_name}
                )
                # print(result)
                result = result.content[0]
                ret_dict = json.loads(result.text)
                retval = ret_dict['msg']
            except:
                pass
        return retval

async def main(inout, mcp_url):
    client = mcp_client(inout, mcp_url)
    await client.run()

if __name__ == '__main__':
    running = True
    while running:
        inout = None
        try:
            inout = std_io()
            inout.start()
            asyncio.run(main(inout, mcp_url))
        except KeyboardInterrupt:
            print('Program interrupted by user')
            running = False
        except Exception as e:
            print(e)
        finally:
            if inout:
                inout.stop()
