import datetime
import json
import os
import random
import shutil
import string

import patoolib
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.http import HttpResponseBadRequest
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import FileNode

# Directory of the mounted volumes
BASE_DIR = '/volumes'


@login_required
def keep_alive(request):
    '''
    Function to keep alive the session
    :param request: Request Object
    :return: JsonResponse with HTTP 200 OK
    '''
    request.session.modified = True
    return JsonResponse({'status': 'ok'})


def extract_archive(request):
    '''
    Function to extract the archive file
    :param request: Request Object containing the path of the archive
    :return: HttpResponse with BadRequest or a Redirect to files page
    '''
    if request.method == 'POST':
        archive_path = request.POST.get('archive_path')
        if not archive_path:
            return HttpResponseBadRequest("Chemin d'archive manquant.")

        archive_full_path = os.path.join(BASE_DIR, archive_path)
        print("archive_full_path :", archive_full_path)
        extract_to = os.path.dirname(archive_full_path)
        print("extract_to :", extract_to)

        try:
            patoolib.extract_archive(archive_full_path, outdir=extract_to)
        except Exception as e:
            print("Erreur lors de l'extraction :", e)
            return HttpResponseBadRequest("Erreur d'extraction.")

        return redirect('file_tree')

    return HttpResponseBadRequest("Méthode non autorisée.")


def get_octal_permissions(file_path):
    return oct(os.stat(file_path).st_mode)[-3:]


def octal_to_string(octal):
    result = ""
    value_letters = [(4, "r"), (2, "w"), (1, "x")]
    for digit in [int(n) for n in str(octal)]:
        for value, letter in value_letters:
            if digit >= value:
                result += letter
                digit -= value
            else:
                result += "-"
    return result


def get_directory_structure(rootdir):
    def build_tree(current_path, rel_path=""):
        '''
        Function to build a tree structure based on the current path
        :param current_path: Path of the root directory
        :param rel_path:
        :return: Dictionary containing a tree structure of the files and folders
        '''
        tree = []
        try:
            for item in os.listdir(current_path):
                if item[0] == ".":
                    continue
                full_path = os.path.join(current_path, item)
                rel_item_path = os.path.join(rel_path, item)
                if os.path.isdir(full_path):
                    tree.append({
                        'name': item,
                        'full_path': rel_item_path,
                        'type': 'folder',
                        'rights': octal_to_string(get_octal_permissions(full_path)),
                        'lastmodified': datetime.datetime.fromtimestamp(os.path.getmtime(full_path)),
                        'children': build_tree(full_path, rel_item_path),
                        'size': get_size(full_path, False, 0)
                    })
                else:
                    tree.append({
                        'name': item,
                        'full_path': rel_item_path,
                        'type': 'file',
                        'lastmodified': datetime.datetime.fromtimestamp(os.path.getmtime(full_path)),
                        'rights': octal_to_string(get_octal_permissions(full_path)),
                        'size': get_size(full_path, False, 0)
                    })
        except PermissionError:
            pass
        return tree

    return build_tree(rootdir)


@csrf_exempt
def move_item(request):
    '''
    Function used to move a file or a folder
    :param request: Request Object containing the path of the file/folder and the destination path
    :return:
    '''
    if request.method == 'POST':
        data = json.loads(request.body)
        source = BASE_DIR + "/" + data.get("source_path")
        destination = BASE_DIR + "/" + data.get('destination_path')
        print(f'source: {source}, destination: {destination}')
        if source and destination:
            filename = os.path.basename(source)
            print(f'filename: {filename}')
            new_path = os.path.join(destination, filename)
            print(f"new_path: {new_path}")
            try:
                shutil.move(source, new_path)
                return JsonResponse({'status': 'success'})
            except Exception as e:
                print(e)
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@ensure_csrf_cookie
def file_tree_view(request):
    """
    Function used to display the file tree
    :param request: Request Object containing the session information (to know if user is logged in)
    :return: The page using the tree and a template
    """
    if not request.session.get('authenticated'):
        return redirect('login')
    tree = get_directory_structure(BASE_DIR)
    return render(request, 'file_tree.html', {'tree': tree, 'root_name': os.path.basename(BASE_DIR)})


def download_file(request, path):
    '''
    Function used to download a file
    :param request:
    :param path: Path of the file
    :return: HttpResponse 404 if error or FileResponse with the selected file if no error
    '''
    file_path = os.path.join(BASE_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True)
    raise Http404("Fichier non trouvé")


@csrf_protect
def upload_file(request):
    '''
    Function used to upload a file
    :param request: Request Object containing the uploaded file and the path where it has to be uploaded
    :return: HttpResponse with BadRequest or a Redirect to files page
    '''
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        target_path = request.POST.get('target_path', '').strip('/')

        if not uploaded_file:
            return HttpResponseBadRequest("Aucun fichier reçu.")

        save_path = os.path.join(BASE_DIR, target_path, uploaded_file.name)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        return redirect('file_tree')

    return HttpResponseBadRequest("Méthode non autorisée.")


@csrf_exempt
def delete_item(request):
    '''
    Function used to delete a file or a folder
    :param request: Request Object containing the path of the file/folder to delete
    :return:
    '''
    if request.method == 'POST':
        try:
            if request.content_type != 'application/json':
                return JsonResponse({'status': 'error', 'message': 'Content-Type invalide'})

            data = json.loads(request.body)
            path = data.get('path')

            if not path:
                return JsonResponse({'status': 'error', 'message': 'Chemin manquant'})

            full_path = os.path.join(BASE_DIR, path)
            print("full_path", full_path)
            if os.path.exists(full_path):
                if os.path.isfile(full_path):
                    os.remove(full_path)
                elif os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    return JsonResponse({'status': 'error', 'message': 'Type de fichier inconnu'})
                return JsonResponse({'status': 'ok'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Fichier ou dossier introuvable'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    else:
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})


@csrf_exempt
def download_archive(request):
    '''
    Function used to download an archive from a folder.
    :param request: Request Object containing the path of the folder and the format (.zip, .tar.gz ...)
    :return: Return error message if error, or FileResponse with the archived folder if no error
    '''
    if request.method != 'POST':
        raise Http404("Méthode non autorisée.")

    folder_path = BASE_DIR + "/" + request.POST.get('folder_path')
    archive_format = request.POST.get('format', 'zip')
    if not folder_path or not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        raise Http404("Dossier introuvable.")

    max_size = 10 * 1024 * 1024 if archive_format == 'zip' else 30 * 1024 * 1024
    folder_size = get_size(folder_path, True, max_size)
    if folder_size > max_size:
        messages.error(
            request,
            f"Le dossier est trop volumineux pour être archivé en .{archive_format} (taille max autorisée : 10Mo pour .zip et 30Mo pour .tar.gz)."
        )
        return redirect(request.META.get('HTTP_REFERER', '/'))

    folder_name = os.path.basename(folder_path.rstrip("/"))
    archive_name = os.path.join(BASE_DIR, folder_name)

    try:
        if archive_format == "zip":
            archive_file = shutil.make_archive(archive_name, 'zip', folder_path)
            mime = "application/zip"
        elif archive_format == "tar":
            archive_file = shutil.make_archive(archive_name, 'gztar', folder_path)
            mime = "application/gzip"
        else:
            raise Http404("Format non supporté.")

        return FileResponse(open(archive_file, 'rb'),
                            as_attachment=True,
                            filename=os.path.basename(archive_file),
                            content_type=mime)
    finally:
        os.remove(archive_file)


def create_folder(request):
    '''
    Function used to create a folder
    :param request: Request Object containing the path of the folder's parent, and the name of the folder
    :return: Redirect to files
    '''
    if request.method == 'POST':
        parent_path = request.POST.get('parent_path') or ''
        folder_name = request.POST.get('folder_name')
        full_path = os.path.join(parent_path, folder_name).strip("/")
        print(f"full path : {full_path}")
        os.makedirs(os.path.join("/volumes/", full_path), exist_ok=True)
        FileNode.objects.create(name=folder_name, type='folder', full_path=full_path)
        return redirect('file_tree')


@csrf_exempt
def edit_file(request):
    '''
    Function used to edit a file
    :param request: Request Object containing the path of the file and the new content
    :return: HttpResponse with BadRequest if error, JsonResponse with "OK" otherwise
    '''
    if request.method == 'GET':
        print("GET")
        path = request.GET.get('path')
        full_path = os.path.join(BASE_DIR, path)
        print(f"full path : {full_path}")
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return HttpResponse(f.read())
        return HttpResponseBadRequest("Fichier non trouvé.")

    elif request.method == 'POST':
        print("POST")
        data = json.loads(request.body)
        path = data.get('path')
        content = data.get('content')
        full_path = os.path.join(BASE_DIR, path)
        print(f"full path : {full_path}")
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return JsonResponse({"status": "ok"})
        except Exception as e:
            return HttpResponseBadRequest(f"Erreur: {e}")


def login_view(request):
    '''
    Function used in the login page, to authenticate a user
    :param request: Request Object containing the uploaded file to authenticate
    :return: Login page with error if authentication failed, Redirect to files otherwise
    '''
    error = None
    if request.method == 'POST' and request.FILES.get('authfile'):
        uploaded_file = request.FILES['authfile']
        uploaded_content = uploaded_file.read()
        stored_path = os.path.join('/volumes', '.dockerToolboxKey')
        try:
            with open(stored_path, 'rb') as f:
                stored_content = f.read()

            if uploaded_content == stored_content:
                request.session['authenticated'] = True
                return redirect('/files')
            else:
                error = "Fichier incorrect"

        except FileNotFoundError:
            error = "Fichier de référence introuvable (/volumes/.dockerToolboxKey)"

    return render(request, 'login.html', {'error': error})


def logout_view(request):
    '''
    Function used to logout a user
    :param request: Request Object containing the session information
    :return: Redirect to login page
    '''
    request.session.flush()
    return redirect('login')


def generate_random_string(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def create_volume_file(path):
    random = generate_random_string(10)
    with open(path, 'w') as f:
        f.write(f"{random}")


def get_size(path, block, size):
    '''
    Function used to get the size of a file or folder
    :param path: Path of folder or file
    :param size: Maximum size before the for loop stops and return the total
    :param block: True or False, to return size at the moment total > size
    :return: Size of file or folder
    '''
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
                if block:
                    if total > size:
                        return total
            except:
                pass
    return total
